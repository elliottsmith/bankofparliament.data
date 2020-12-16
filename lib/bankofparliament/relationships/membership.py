"""
Module for membership relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .relationships import TextRelationship


class Membership(TextRelationship):
    """Directorship relationship solver"""

    def cleanup(self):
        """Clean the text prior to solving"""

    def solve(self):
        """Find entity in text"""
        filt = (
            self.parent._extracted_entities["name"].str.lower()
            == self.relationship["target"].lower()
        )
        target_entity = self.parent._extracted_entities.loc[filt]
        for (_index, row) in target_entity.iterrows():
            entity = row.to_dict()
            self.extracted_entities.append(entity)
