"""
Module for crawl related tasks
"""
# -*- coding: utf-8 -*-

# sys libs

# third party libs
import pandas

# local libs


class CrawlEntities:
    """Crawls for more entity info"""

    def __init__(self, entities, logger):
        """Initialise the crawl class"""
        self.entities = pandas.read_csv(entities)
        self.logger = logger

    def execute(self):
        """"""
        print(self.entities)
