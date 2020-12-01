"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import re
import ast
import json

# third party
import pandas
import spacy

# local libs
from .utils import (
    read_csv_as_dataframe,
    get_companies_house_company_name_from_number,
    get_request,
    extract_company_registration_number_from_text,
    reconcile_company_names,
)
from .constants import (
    ENTITY_TEMPLATE,
    NER_BASE_MODEL,
    COMPANIES_HOUSE_PREFIXES,
    OPENCORPORATES_RECONCILE_URL,
    HEADERS,
)
from .custom import ValueOverride


class NamedEntityExtract:
    """Class to extract entities from raw data"""

    START = 0
    END = -1

    def __init__(
        self,
        entities,
        relationships,
        custom_entities,
        custom_relationships,
        companies_house_apikey,
        opencorporates_apikey,
        logger,
        ner_model=None,
    ):
        """Read all passed in data files"""
        self.companies_house_apikey = companies_house_apikey
        self.opencorporates_apikey = opencorporates_apikey
        self.logger = logger
        _entities = read_csv_as_dataframe(entities)
        _relationships = read_csv_as_dataframe(relationships)
        _custom_entities = read_csv_as_dataframe(custom_entities)
        _custom_relationships = read_csv_as_dataframe(custom_relationships)

        entity_data_frames = [_entities]
        if len(_custom_entities):
            entity_data_frames.append(_custom_entities)

        self._all_entities = pandas.concat(entity_data_frames, ignore_index=True)

        relationships_data_frames = [_relationships]
        if len(_custom_relationships):
            relationships_data_frames.append(_custom_relationships)

        self._all_relationships = pandas.concat(
            relationships_data_frames, ignore_index=True
        )[self.START : self.END]

        model = ner_model if ner_model else NER_BASE_MODEL
        self.logger.info("Loading NER model: {}".format(model))
        self.nlp = spacy.load(model)
        self.output_dir = os.path.dirname(entities)
        self.missing = []

    def execute(self):
        """Execute"""
        self.extract_entities_from_relationships()
        self.save()

        self.logger.info("*" * 100)
        self.logger.info(
            "Unknown Entities: {}/{}".format(len(self.missing), len(self.relationships))
        )
        self.logger.info("*" * 100)

    @property
    def entities(self):
        return self._all_entities

    @property
    def relationships(self):
        return self._all_relationships

    def extract_entities_from_relationships(self):
        """Extract entities from the relationships"""

        for (index, relationship) in self.relationships.iterrows():
            relationship_type = relationship["relationship_type"]

            if relationship_type == "member_of":
                pass

            elif relationship_type == "related_to":
                self._process(index, relationship, ["PERSON"])

            elif relationship_type == "owner_of":
                self._process_property(index, relationship)

            elif relationship_type == "employed_by":
                self._process(index, relationship, ["ORG", "NORP"])

            elif relationship_type == "sponsored_by":
                self._process(index, relationship, ["PERSON", "ORG", "NORP"])

            elif relationship_type == "director_of":
                self._process(index, relationship, ["ORG", "NORP"])

            elif relationship_type == "shareholder_of":
                self._process(index, relationship, ["ORG", "NORP"])

            elif relationship_type == "significant_control_of":
                self._process(index, relationship, ["ORG", "NORP"])

            elif relationship_type == "miscellaneous":
                self._process(index, relationship, ["PERSON", "ORG", "NORP"])

            elif relationship_type == "donations_from":
                self._process_multi_from(index, relationship)

            elif relationship_type == "gifts_from":
                self._process_multi_from(index, relationship)

            elif relationship_type == "visited":
                self._process_multi_from(index, relationship)

            else:
                self.logger.warning(
                    "Missing relationshtip type: {}".format(relationship_type)
                )

    def _process(self, index, relationship, ner_types):
        """
        Process relationship
        """
        _target = relationship["target"]
        _text = relationship["text"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target = "UNKNOWN"
        target_entity_type = None
        text = self.eval_list_as_strings(_text)[0]

        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ner_types:
                target = entity[0].title()
                target_entity_type = self.get_target_type(entity[1])
                break

        relationship["target"] = target
        relationship["date"] = self.extract_date_from_text(text)
        relationship["amount"] = self.extract_amount_from_text(text)
        self.log_relationship(index, relationship)

        if target != "UNKNOWN":
            self.add_entity(entity_type=target_entity_type, name=target, aliases=target)

    def _process_property(self, index, relationship):
        """
        Process property ownership
        """
        _target = relationship["target"]
        _text = relationship["text"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target = "UNKNOWN"
        target_entity_type = None
        text = self.eval_list_as_strings(_text)[0]

        amount = 0
        if "(i)" in text:  # indicates wealth
            amount = 0
        if "(ii)" in text:  # indicates income from property
            amount = 10000

        clean_string = text.split(":")[0]
        result = self.nlp(clean_string)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["GPE", "LOC"]:
                target = entity[0].title()
                target_entity_type = self.get_target_type(entity[1])
                break

        relationship["target"] = target
        relationship["date"] = self.extract_date_from_text(text)
        relationship["amount"] = amount
        self.log_relationship(index, relationship)

        if target != "UNKNOWN":
            self.add_entity(entity_type=target_entity_type, name=target, aliases=target)

    def _process_multi_from(self, index, relationship):
        """
        Process multi line text info
        """
        _target = relationship["target"]
        _text = relationship["text"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target = "UNKNOWN"
        company_registration = "N/A"
        target_entity_type = None
        text = self.eval_list_as_strings(_text)

        _data = {}
        for line in text:
            if ":" in line:
                splits = line.split(":")
                key = splits[0].strip()
                value = splits[-1].strip()
                if "name" in key.lower():

                    custom_value = ValueOverride(
                        "swap_values.csv", value.strip(), self.logger
                    )
                    if custom_value.converted:
                        self.logger.debug(
                            "Found override: {}".format(custom_value.value)
                        )
                        value = custom_value.value

                    _data["name"] = value
                elif "amount" in key.lower() or "value" in key.lower():
                    _data["amount"] = value

                elif "status" in key.lower():
                    _data["status"] = value

                elif "address" in key.lower():
                    _data["address"] = value

            if "registered" in line.lower():
                _data["date"] = line

        # before we do NER extraction, see if we can find a company number
        if "status" in _data and "individual" in _data["status"].lower():
            pass

        elif (
            "status" in _data
            and not "trade union" in _data["status"].lower()
            and not "association" in _data["status"].lower()
            and not "trust" in _data["status"].lower()
            and not "other" in _data["status"].lower()
        ):
            company_name = None

            # find the company number from the text
            company_registration_number = extract_company_registration_number_from_text(
                _data["status"], self.logger
            )
            if company_registration_number:
                # query companies house for company
                company_name = get_companies_house_company_name_from_number(
                    self.companies_house_apikey,
                    company_registration_number,
                    self.logger,
                )

            if not company_name:
                # either the company_registration_number is invalid or
                # it is outside the companies house jurisdiction
                data = reconcile_company_names(_data["name"], self.logger)
                results = data[_data["name"]]["result"]
                if len(results):
                    top_match = results[0]
                    if top_match["score"] > 10:
                        company_name = top_match["name"]
                        company_registration_number = top_match["id"].split("/")[-1]

            if company_name:
                target_entity_type = "company"
                target = company_name
                company_registration = company_registration_number
                self.companies_found += 1
                self.logger.info(
                    "Company Found: {} ({})".format(company_name, company_registration)
                )
            else:
                self.logger.warning(
                    "Company NOT Found: {}".format(relationship["text"])
                )

        if target == "UNKNOWN":
            result = self.nlp(_data.get("name", _text))
            entities = [(X.text, X.label_) for X in result.ents]
            for entity in entities:
                if entity[1] in ["PERSON", "ORG", "NORP"]:
                    target = entity[0].title()
                    target_entity_type = self.get_target_type(entity[1])
                    break

        relationship["target"] = target
        relationship["date"] = self.extract_date_from_text(_data.get("date", _text))
        relationship["amount"] = self.extract_amount_from_text(
            _data.get("amount", _text)
        )

        self.log_relationship(index, relationship)

        if target != "UNKNOWN":
            self.add_entity(
                entity_type=target_entity_type,
                name=target,
                company_registration=company_registration,
                aliases=target,
            )

    ##########################################################################################
    # Genral Methods
    ##########################################################################################

    def add_entity(self, **kwargs):
        """Add entity data"""
        data = dict.fromkeys(ENTITY_TEMPLATE)
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value if value else "N/A"
            else:
                self.logger.debug("Key not found in template: {}".format(key))

        new_entity = pandas.DataFrame([data])
        self._all_entities = pandas.concat(
            [self._all_entities, new_entity], ignore_index=True
        )

    def get_target_type(self, ner_type):
        """Convert NER type to node type"""
        _data = {
            "PERSON": "person",
            "ORG": "company",
            "NORP": "company",
            "LOC": "place",
            "GPE": "place",
        }
        return _data[ner_type]

    def eval_list_as_strings(self, _list):
        """Eval the string to list"""
        lines = [line.strip() for line in ast.literal_eval(_list)] if _list else []
        return lines

    def extract_date_from_text(self, text):
        """Extract date from text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["DATE"]:
                return entity[0]
        return None

    def extract_amount_from_text(self, text):
        """Extract monetary amount from text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["MONEY"]:
                pounds = entity[0].split(".")[0]
                return re.sub("[^0-9]", "", pounds)
        return 0

    def log_relationship(self, index, relationship, prefix="Relationship"):
        """Log the relationship"""
        source = relationship["source"]
        relationship_type = relationship["relationship_type"]
        target = relationship["target"]
        self.logger.info(
            "{:05d}/{:05d} - {}: {} ({}) {}".format(
                index,
                len(self.relationships),
                prefix,
                source,
                relationship_type,
                target,
            )
        )
        if target == "UNKNOWN":
            self.missing.append(relationship)

    def save(self):
        """Dump the rows to csv"""
        if not os.path.exists(self.output_dir):
            self.logger.debug("Making directoy: {}".format(self.output_dir))
            os.makedirs(self.output_dir)

        self.relationships.to_csv(
            os.path.join(self.output_dir, "relationships_extracted.csv"),
            index_label="id",
        )
        self.entities.to_csv(
            os.path.join(self.output_dir, "entities_extracted.csv"), index_label="id"
        )
        self.logger.info("Saved: {}".format(self.output_dir))
