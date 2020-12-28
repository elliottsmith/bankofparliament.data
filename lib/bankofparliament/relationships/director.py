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
    strip_punctuation,
)
from ..constants import POLLITICAL_ENTITIES, OTHER_ENTITIES
from ..patterns import POSITIONS


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
        text = strip_parenthesis_text(text)
        text = strip_registered_text(text)
        text = strip_positions_text(text)
        text = strip_from_dates_text(text)

        text = self.split(text)
        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)
        text = self.run_replace(text)

        # build texts to query
        nlp_names = self.get_nlp_entities_from_text(
            text=self.text, entity_types=["ORG", "PERSON"]
        )

        # clean name
        names_to_try = [text]

        # nlp names
        for nlp in nlp_names:
            if (
                not nlp in POSITIONS
                and len(nlp.split()) > 1
                and nlp.lower() not in self.EXCLUDE_FROM_NLP
            ):
                names_to_try.append(strip_punctuation(nlp.lower()))
                names_to_try.append(nlp.lower())

        names_to_try = list(set(names_to_try))
        self.names_to_try = names_to_try

        self.text = text

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        # do a much wider search, across all jurisdictions for both
        # corporates and charities, schools etc
        for name in self.names_to_try:
            if name.lower() not in self.EXCLUDE_FROM_SEARCHING:
                entity = self.find_organisation_from_text(text=name)
                if entity:
                    self.extracted_entities.append(entity)
                    return
