"""
Module for gift relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .relationships import CompoundRelationship
from ..constants import ENTITY_TYPES


class Gift(CompoundRelationship):
    """Gift relationship solver"""

    ALIAS_ENTITY_TYPES = ENTITY_TYPES

    def cleanup(self):
        """Clean the text prior to solving"""
        self.entity_type = self.get_entity_type_from_status()
        self.text["name"] = self.text["name"].replace(" & ", " and ")

        multi_entry_regex = r"\([0-9]+\) ([a-zA-Z ]+)"
        multi_match = re.findall(multi_entry_regex, self.text["name"]) or []
        self._entries = multi_match if multi_match else [self.text["name"]]

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.text["date"])
        self.amount = self.extract_amount_from_text(self.text["amount"])

        for entry in self._entries:

            entity = self.find_alias_from_text(text=entry)
            if entity:
                self.extracted_entities.append(entity)
                continue

            if self.entity_type == "company":

                entity = self.find_organisation_from_number_in_text(
                    text=self.text["status"]
                )
                if entity:
                    self.extracted_entities.append(entity)
                    return

                entity = self.find_organisation_from_text(text=entry)
                if entity:
                    self.extracted_entities.append(entity)
                    return
