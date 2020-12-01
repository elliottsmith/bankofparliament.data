"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import re
import ast

# third party
import pandas
import spacy

# local libs
from .utils import read_csv_as_dataframe
from .constants import ENTITY_TEMPLATE, NER_BASE_MODEL


class NamedEntityExtract:
    """Class to extract entities from raw data"""

    LIMIT = -1

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
        self.logger = logger
        self._entities = read_csv_as_dataframe(entities)
        self._relationships = read_csv_as_dataframe(relationships)
        self._custom_entities = read_csv_as_dataframe(custom_entities)
        self._custom_relationships = read_csv_as_dataframe(custom_relationships)

        self._all_entities = pandas.concat(
            [self._entities, self._custom_entities], ignore_index=True
        )
        self._all_relationships = pandas.concat(
            [self._relationships, self._custom_relationships], ignore_index=True
        )[: self.LIMIT]

        model = ner_model if ner_model else NER_BASE_MODEL
        self.logger.info("Loading NER model: {}".format(model))
        self.nlp = spacy.load(model)
        self.output_dir = os.path.dirname(entities)
        self.missing = []

    def execute(self):
        """Execute"""
        self.sanitise_relationships()
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

    def sanitise_relationships(self):
        """Sanitise the relationships"""

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
        target_entity_type = None
        text = self.eval_list_as_strings(_text)

        _data = {}
        for line in text:
            if ":" in line:
                splits = line.split(":")
                key = splits[0]
                value = splits[-1]
                if "name" in key.lower():
                    _data["name"] = "Received something from {}".format(
                        value
                    )  # for ner recognition
                elif "amount" in key.lower() or "value" in key.lower():
                    _data["amount"] = value
            if "registered" in line.lower():
                _data["date"] = line

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
            self.add_entity(entity_type=target_entity_type, name=target, aliases=target)

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
            os.path.join(self.output_dir, "relationships_extracted.csv")
        )
        self.entities.to_csv(os.path.join(self.output_dir, "entities_extracted.csv"))
        self.logger.info("Saved: {}".format(self.output_dir))
