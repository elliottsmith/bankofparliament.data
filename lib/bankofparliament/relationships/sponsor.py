"""
Module for sponsor relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .relationships import TextRelationship
from ..constants import ENTITY_TYPES


class Sponsorship(TextRelationship):
    """Shareholder relationship solver"""

    EXCLUDE = ["house", "parliament", "co-chair", "house of lords"]
    NER_TYPES = ["PERSON"]
    STARTERS = ["the "]
    ALIAS_ENTITY_TYPES = ENTITY_TYPES

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_ner_type_from_text(
            text=self.relationship["text"],
            target_entity_type="person",
        )
        if entity:
            self.extracted_entities.append(entity)
            return

        result = self.nlp(self.text)
        entities = [(X.text, X.label_) for X in result.ents]

        for entity in entities:
            if entity[1] == "ORG":
                entity_name = entity[0]

                for starter in self.STARTERS:
                    if entity_name.lower().startswith(starter):
                        entity_name = entity_name[len(starter) :]
                entity_name = entity_name.strip()

                entity = self.find_organisation_from_text(text=entity_name)
                if entity:
                    self.extracted_entities.append(entity)
                    return
