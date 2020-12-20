"""
Module for donation relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .relationships import CompoundRelationship
from ..constants import ENTITY_TYPES


class Donation(CompoundRelationship):
    """Donation relationship solver"""

    ALIAS_ENTITY_TYPES = ENTITY_TYPES

    def cleanup(self):
        """Clean the text prior to solving"""
        self.entity_type = self.get_entity_type_from_status()
        self.text["name"] = self.text["name"].replace(" & ", " and ")

        multi_entry_regex = r"\([0-9]+\) ([a-zA-Z ]+)"
        multi_match = re.findall(multi_entry_regex, self.text["name"]) or []
        self._entries = multi_match if multi_match else [self.text["name"]]
