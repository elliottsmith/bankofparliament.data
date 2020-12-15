"""
Module for relation relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .base_relationships import TextRelationship
from ..constants import HUMAN_ENTITIES


class Relation(TextRelationship):
    """Family relation relationship solver"""

    NER_TYPES = ["PERSON"]
    ALIAS_ENTITY_TYPES = HUMAN_ENTITIES

    def solve(self):
        """Find entity in text"""
        entities_found = False
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        result = self.nlp(self.text)
        entities = [(X.text, X.label_) for X in result.ents]

        for entity in entities:
            if entity[1] in self.NER_TYPES:
                entity_name = entity[0]

                if len(entity_name.split()) > 1:
                    entity = self.make_entity_dict(
                        entity_type="person",
                        name=entity_name,
                        aliases=";".join([entity_name]),
                    )
                    entities_found = True
                    self.extracted_entities.append(entity)

        if not entities_found:
            alias = self.check_aliases(entity_types=self.ALIAS_ENTITY_TYPES)
            if alias:
                entity = self.make_entity_dict(
                    entity_type="person",
                    name=alias,
                    aliases=";".join([alias]),
                )
                entities_found = True
                self.extracted_entities.append(entity)
