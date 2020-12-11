"""
Module for membership relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .base import TextRelationship


class Membership(TextRelationship):
    """Directorship relationship solver"""

    def cleanup(self):
        """Clean the text prior to solving"""

    def solve(self):
        """Find entity in text"""
