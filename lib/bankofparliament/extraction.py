"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os

# third party
import pandas

# local libs
from .utils import read_csv_as_dataframe


class NamedEntityExtract:
    """Class to extract entities from raw data"""

    LIMIT = 100

    def __init__(
        self,
        entities,
        relationships,
        custom_entities,
        custom_relationships,
        companies_house_apikey,
        opencorporates_apikey,
        logger,
    ):
        """Read all passed in data files"""
        self.logger = logger
        self._entities = read_csv_as_dataframe(entities)
        self._relationships = read_csv_as_dataframe(relationships)
        self._custom_entities = read_csv_as_dataframe(custom_entities)
        self._custom_relationships = read_csv_as_dataframe(custom_relationships)

        self.output_dir = os.path.dirname(entities)

    def execute(self):
        """Execute"""
        self.sanitise_relationships()
        self.save()

    @property
    def entities(self):
        return pandas.concat([self._entities, self._custom_entities], ignore_index=True)

    @property
    def relationships(self):
        return pandas.concat(
            [self._relationships, self._custom_relationships], ignore_index=True
        )[: self.LIMIT]

    def sanitise_relationships(self):
        """Sanitise the relationships"""

        for (index, relationship) in self.relationships.iterrows():

            source = relationship["source"]
            relationship_type = relationship["relationship_type"]
            target = relationship["target"]
            self.logger.info(
                "Relationship: {} ({}) {}".format(source, relationship_type, target)
            )

    def save(self):
        """Dump the rows to csv"""
        if not os.path.exists(self.output_dir):
            self.logger.debug("Making directoy: {}".format(self.output_dir))
            os.makedirs(self.output_dir)

        self.relationships.to_csv(
            os.path.join(self.output_dir, "relationships_extracted.csv")
        )
        self.entities.to_csv(os.path.join(self.output_dir, "entities_extracted.csv"))
        self.logger.info("Saved: {}".format((self.output_dir)))
