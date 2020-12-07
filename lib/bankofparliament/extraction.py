"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import time

# third party
import pandas
import spacy

# local libs
from .utils import read_csv_as_dataframe
from .constants import NER_BASE_MODEL
from .relationships.base import get_relationship_solver


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

    def execute(self):
        """Execute"""
        time_start = time.time()
        self.extract_entities_from_relationships()
        self.save()
        taken = time.time() - time_start

        filt = self.relationships["target"] != "UNKNOWN"
        found = self.relationships.loc[filt]
        self.logger.info(
            "{}/{} ({}%) relationships solved (Time taken: {})".format(
                len(found),
                len(self.relationships[self.START : self.END]),
                int(
                    (len(found) / len(self.relationships[self.START : self.END])) * 100
                ),
                time.strftime("%Hh%Mm%Ss", time.gmtime(taken)),
            )
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

            if (
                relationship["source"] != "UNKNOWN"
                and relationship["target"] != "UNKNOWN"
                and self.entity_name_exists(relationship["source"])
                and self.entity_name_exists(relationship["target"])
            ):
                continue

            solver = get_relationship_solver(
                index=index,
                relationship=relationship,
                entities=self.entities,
                nlp=self.nlp,
                companies_house_apikey=self.companies_house_apikey,
                opencorporates_apikey=self.opencorporates_apikey,
                logger=self.logger,
            )

            if solver:
                solver.solve()
                for entity in solver.extracted_entities:
                    self.add_entity(entity)

    def add_entity(self, entity):
        """Add entity data"""
        entity_name = entity["name"]
        if not self.entity_name_exists(entity_name):
            new_entity = pandas.DataFrame([entity])
            self._all_entities = pandas.concat(
                [self._all_entities, new_entity], ignore_index=True
            )

    def entity_name_exists(self, name):
        """Check if entity name already exists"""
        filt = self.entities["name"].str.lower() == name.lower()
        entity = self.entities.loc[filt]
        if len(entity):
            self.logger.debug("Entity exists: {}".format(name))
            return True
        return False

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
