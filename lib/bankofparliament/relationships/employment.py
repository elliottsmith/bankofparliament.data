"""
Module for employment relationship
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
from ..utils import colorize
from ..constants import ENTITY_TYPES


class Employment(TextRelationship):
    """Employment relationship solver"""

    TARGET_ENTITY_TYPE = "company"
    ALIAS_ENTITY_TYPES = ENTITY_TYPES
    PREFERRED_ALIAS_ENTITY_TYPES = ["company", "pollster"]

    SPLITTERS = ["speaker", "engagement", "speaking"]
    STARTERS = ["and ", ",", "of ", "in ", "group"]
    ENDERS = ["."]
    REPLACE = [("  ", " "), (" & ", " and ")]

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)
        text = strip_from_dates_text(text)
        text = strip_parenthesis_text(text)
        text = strip_positions_text(text)

        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)
        text = self.run_replace(text)
        self.text = text

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        # recurring payments
        recurring = self.recurring_payment_regex.search(
            self.relationship["text"].lower()
        )
        if recurring:
            self.logger.debug(
                "{}: {}".format(
                    colorize("Recurring payment set", "light blue"),
                    self.relationship["text"],
                )
            )
            self.amount = "recurring"

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_organisation_from_text(text=self.text)
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_single_payment_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_profession_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return
