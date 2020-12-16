"""
Module for significant relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .relationships import TextRelationship
from ..patterns import IN_PARENTHESIS
from ..constants import OTHER_ENTITIES


class SignificationControl(TextRelationship):
    """Signification control relationship solver"""

    NER_TYPES = ["ORG"]
    ALIAS_ENTITY_TYPES = OTHER_ENTITIES

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text

        regex_pattern = ""
        for item in IN_PARENTHESIS:
            regex_pattern += r"\(.*{}.*\)|".format(item)
        regex_pattern = "({})".format(regex_pattern[:-1])

        match = re.search(regex_pattern, text)
        if match:
            groups = match.groups()
            for grp in groups:
                text = text.replace(grp, "")

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
