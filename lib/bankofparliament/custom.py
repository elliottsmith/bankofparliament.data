"""
Module for custom values
"""
# -*- coding: utf-8 -*-

# sys libs
import os

# third party libs
import pandas


class SwapValue:
    """Class to map one value to another"""

    SWAP_VALUES_FILE = os.path.join(
        os.path.dirname(__file__), "../../data/custom/swap_values.csv"
    )

    def __init__(self, logger):
        self.logger = logger
        if os.path.exists(self.SWAP_VALUES_FILE):
            self.dataframe = self._get_data()
        else:
            self.dataframe = []

    def swap(self, value):
        """Swap the value and return"""
        if len(self.dataframe):
            filt = self.dataframe["from"].str.lower() == value.lower()
            match = self.dataframe.loc[filt, "to"]
            if len(match):
                _value = match.values[0]
                self.logger.info("Overriden:{}".format(_value))
                return _value
        return value

    def _get_data(self):
        """Read csv input file"""
        with open(self.SWAP_VALUES_FILE, "r") as file:
            return pandas.read_csv(file)
