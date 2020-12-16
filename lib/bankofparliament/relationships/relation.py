"""
Module for relation relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .relationships import TextRelationship
from ..constants import HUMAN_ENTITIES


class Relation(TextRelationship):
    """Family relation relationship solver"""

    NER_TYPES = ["PERSON"]
    ALIAS_ENTITY_TYPES = HUMAN_ENTITIES

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_ner_type_from_text(
            text=self.relationship["text"], target_entity_type="person"
        )
        if entity:
            self.extracted_entities.append(entity)
            return
