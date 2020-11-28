"""
Module for download related tasks
"""
# -*- coding: utf-8 -*-

# sys libs
import os

# third party libs
import pandas


class ValueOverride:
    """Class to map one value to another"""

    CUSTOM_DATA = os.path.join(os.path.dirname(__file__), "../../data/custom")

    def __init__(self, dataset_name, value_to_replace, logger):
        self.logger = logger
        self.dataset_name = dataset_name
        self.value_to_replace = value_to_replace
        self._value = value_to_replace

        self.dataset_path = os.path.join(self.CUSTOM_DATA, self.dataset_name)
        if os.path.exists(self.dataset_path):
            dataframe = self._get_data()
            filt = dataframe["from"] == value_to_replace
            match = dataframe.loc[filt, "to"]
            if len(match):
                self._value = match.values[0]
                self.logger.info("Overriden:{}".format(self._value))

    @property
    def value(self):
        return self._value

    @property
    def converted(self):
        return self._value != self.value_to_replace

    def _get_data(self):
        """Read csv input file"""
        with open(self.dataset_path, "r") as file:
            return pandas.read_csv(file)
