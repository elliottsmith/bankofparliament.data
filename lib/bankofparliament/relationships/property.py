"""
Module for property ownership relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import math

# local libs
from .relationships import TextRelationship
from ..text import get_property_multiplier
from ..utils import make_entity_dict


class PropertyOwner(TextRelationship):
    """Property relationship solver"""

    def cleanup(self):
        """Clean the text prior to solving"""

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = 10000 if "(ii)" in self.relationship["text"] else 0

        multiplier = get_property_multiplier(self.relationship["text"])
        if multiplier < 1:
            self.amount = self.amount * multiplier

        for _i in range(math.ceil(multiplier)):
            entity = make_entity_dict(
                entity_type="property",
                name="Property",
            )
            self.extracted_entities.append(entity)
