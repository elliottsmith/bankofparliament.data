"""
Module for directorship relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .relationships import TextRelationship
from ..text import (
    strip_category_text,
    strip_registered_text,
    strip_positions_text,
    strip_from_dates_text,
    strip_parenthesis_text,
)
from ..constants import POLLITICAL_ENTITIES, OTHER_ENTITIES


class Directorship(TextRelationship):
    """Directorship relationship solver"""

    TARGET_ENTITY_TYPE = "company"
    SPLITTERS = ["trading as ", "investee companies", ";"]
    STARTERS = ["and ", ", ", "of "]
    ENDERS = ["."]
    NER_TYPES = ["ORG"]
    ALIAS_ENTITY_TYPES = POLLITICAL_ENTITIES + OTHER_ENTITIES

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)
        text = strip_positions_text(text)
        text = strip_from_dates_text(text)
        text = strip_parenthesis_text(text)

        text = self.split(text)
        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)
        text = self.run_replace(text)
        self.text = text

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_organisation_from_text(text=self.text)
        if entity:
            self.extracted_entities.append(entity)
            return
