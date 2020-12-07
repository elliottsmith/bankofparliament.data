"""
Module for extraction classes
"""
# -*- coding: utf-8 -*-

# local libs
from ..text import eval_string_as_list
from ..custom import SwapValue

class BaseExtractor:
    """Base class for extracting named entities from relationship text"""
    def __init__(self, relationship, logger):
        """Init the base class"""
        self.relationship = relationship
        self.logger = logger
        self.swap_value = SwapValue(logger)

    def execute(self):
        """Execute"""
        texts = self.eval_string_as_list(self.relationship)


    def cleanup_string(self, text):
        """"""
        return text

    def eval_string_as_list(self, text):
        """Literal eval string as list"""
        return eval_string_as_list(text)

