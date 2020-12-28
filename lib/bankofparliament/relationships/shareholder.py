"""
Module for shareholder relationship
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
    strip_share_class,
)
from ..constants import OTHER_ENTITIES, POLLITICAL_ENTITIES


class Shareholder(TextRelationship):
    """Shareholder relationship solver"""

    TARGET_ENTITY_TYPE = "company"
    SPLITTERS = [
        "trading as ",
        "investee companies",
        ";",
        ":",
        ", a",
        ", marketing consultancy",
        ", financial services company",
        ", psychology assessment",
        ", tour operator",
        ", shares co-owned",
        ". UK property company",
        ", Sporting Video Company",
        ", management of",
        "family business",
        "in the EdTech space",
        "SIPP",
        "per cent ownership",
        r"% ownership",
    ]
    STARTERS = ["and ", ", ", "of ", "in "]
    ENDERS = ["."]
    NER_TYPES = ["ORG"]
    ALIAS_ENTITY_TYPES = OTHER_ENTITIES + POLLITICAL_ENTITIES

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_share_class(self.nlp, text)
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
