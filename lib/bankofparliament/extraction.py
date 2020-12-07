"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import re

# third party
import pandas
import spacy

# local libs
from .utils import (
    read_csv_as_dataframe,
    reconcile_company_name,
    colorize,
)
from .constants import (
    ENTITY_TEMPLATE,
    NER_BASE_MODEL,
)
from .custom import SwapValue
from .text import (
    clean_up_significant_control,
    clean_up_directorship,
    eval_string_as_list,
)

from .relationships.base import get_relationship

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

        self.swap_value = SwapValue(self.logger)

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

    def execute(self):
        """Execute"""
        self.extract_entities_from_relationships()
        self.save()

        filt = self.relationships["target"] != "UNKNOWN"
        found = self.relationships.loc[filt]
        self.logger.info(
            "{}/{} relationships solved".format(len(found), len(self.relationships))
        )

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

            relationship_object = get_relationship(index, relationship, self.entities)
            self.logger.debug(relationship_object)

    def _process_organisations(self, index, relationship, organisations):
        """Process organisations"""
        for text in organisations:
            self._process_organisation(index, relationship, text)

    def _process_organisation(self, index, relationship, _text):
        """
        Process organisation
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        company_name = None
        company_registration = None

        data = reconcile_company_name(_text, self.logger)
        results = data["result"]
        if len(results):
            top_match = results[0]
            if top_match["score"] > 10:
                company_name = top_match["name"]
                company_registration = top_match["id"].split("/")[-1]
        else:
            # we aren't able to reconcile this name, we should now do
            # a search of opencorporates, may yield better results,
            # match a prevous company name
            # TODO
            pass

        relationship["target"] = company_name if company_name else "UNKNOWN"
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = self.extract_amount_from_text(_text)

        if company_name and company_registration:
            self.logger.info(
                "Company Found: {} ({}) [Query Name: {}]".format(
                    colorize(company_name, "yellow"),
                    company_registration,
                    colorize(_text, "light blue"),
                )
            )
            self.add_entity(
                entity_type="company",
                name=company_name,
                aliases=[company_name, _text],
                company_registration=company_registration,
            )
        else:
            self.logger.warning(
                "Company NOT Found: {} [Query Name: {}]".format(
                    colorize(relationship["text"], "light red"), _text
                )
            )

        self.log_relationship(index, relationship)

    def _process_people(self, index, relationship, people):
        """Process people"""
        for text in people:
            self._process_person(index, relationship, text)

    def _process_person(self, index, relationship, _text):
        """
        Process person
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target_name = None

        result = self.nlp(_text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["PERSON"]:
                target_name = entity[0].title()
                break

        relationship["target"] = target_name if target_name else "UNKNOWN"
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = self.extract_amount_from_text(_text)
        self.log_relationship(index, relationship)

        if target_name:
            self.logger.info(
                "Person Found: {} [Query Name: {}]".format(
                    colorize(target_name, "yellow"), colorize(_text, "light blue")
                )
            )
            self.add_entity(
                entity_type="person",
                name=target_name,
                aliases=[target_name],
            )
        else:
            self.logger.warning(
                "Person NOT Found: {} [Query Name: {}]".format(
                    colorize(relationship["text"], "light red"), _text
                )
            )

    def _process_property(self, index, relationship, _text):
        """
        Process property
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target_name = "Property"

        amount = 0
        if "(i)" in _text:  # indicates wealth
            amount = 0
        if "(ii)" in _text:  # indicates income from property
            amount = 10000

        relationship["target"] = target_name
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = amount
        self.log_relationship(index, relationship)

        if target_name:
            self.logger.info(
                "Property Found: {} [Query Name: {}]".format(
                    colorize(target_name, "yellow"), colorize(_text, "light blue")
                )
            )
            self.add_entity(
                entity_type="property",
                name=target_name,
                aliases=[target_name],
            )
        else:
            self.logger.warning(
                "Property NOT Found: {} [Query Name: {}]".format(
                    colorize(relationship["text"], "light red"), _text
                )
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

        if not self._is_known_entity(data):
            new_entity = pandas.DataFrame([data])
            self._all_entities = pandas.concat(
                [self._all_entities, new_entity], ignore_index=True
            )

    def _is_known_entity(self, data):
        """Is entity known already"""
        _entity_type = data["entity_type"]
        _name = data["name"]

        filt = (self.entities["name"].str.lower() == _name.lower()) & (
            self.entities["entity_type"].str.lower() == _entity_type.lower()
        )
        entity = self.entities.loc[filt]
        if len(entity):
            self.logger.info("Entity exists: {}".format(_name))
            return True
        return False

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
        self.logger.debug(
            "{:05d}/{:05d} - {}: {} ({}) {}".format(
                index,
                len(self.relationships),
                prefix,
                source,
                relationship_type,
                target,
            )
        )

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
