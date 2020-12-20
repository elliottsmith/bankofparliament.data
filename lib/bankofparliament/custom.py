"""
Module for custom values
"""
# -*- coding: utf-8 -*-

# sys libs
import os

# third party libs
import pandas

# local libs
from .utils import (
    make_entity_dict,
    get_list_of_trade_unions,
    get_government_organisations,
    get_universities,
    get_local_authorities,
)


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


class GenerateCustom:
    """Class to output an initial custom data set"""

    def __init__(self, output_path, logger):
        """"""
        self.output_path = output_path
        self.logger = logger
        self.data = []

    def execute(self):
        """Execute custom data gathering methods"""
        self.trade_unions()
        self.universities()
        self.local_authorities()
        self.government_organisations()

    def trade_unions(self):
        """Get all trade unions"""
        unions = get_list_of_trade_unions()
        for union in unions:
            entity = make_entity_dict(name=union, entity_type="union")
            self.data.append(entity)

    def universities(self):
        """Get all UK universities"""
        universities = get_universities(self.logger)
        for university in universities["result"]:
            _id = university["id"]
            _name = university["name"]

            name = _name.replace("({})".format(_id), "")
            name = name.replace("[INACTIVE]", "")
            name = name.strip()

            aliases = [name]
            if "University of " in name:
                _alias = " ".join(name.split(" of ")[::-1])
                aliases.append(_alias)

            entity = make_entity_dict(
                name=name,
                entity_type="university",
                aliases=aliases,
            )
            self.data.append(entity)

    def local_authorities(self):
        """Get all local authorities"""
        local_authorities = get_local_authorities(self.logger)

        for local_authority in local_authorities["result"]:
            _id = local_authority["id"]
            _name = local_authority["name"]

            name = _name.replace("({})".format(_id), "")
            name = name.replace("[INACTIVE]", "")
            name = name.strip()

            aliases = [name]
            if " Borough " in name:
                _alias = " ".join(name.split(" Borough "))
                aliases.append(_alias)

            entity = make_entity_dict(
                name=name,
                entity_type="local_authority",
                aliases=aliases,
            )
            self.data.append(entity)

    def government_organisations(self):
        """Get all government orgs"""
        gov_orgs = get_government_organisations(self.logger)

        for gov_org in gov_orgs["result"]:
            _id = gov_org["id"]
            _name = gov_org["name"]

            name = _name.replace("({})".format(_id), "")
            name = name.replace("[INACTIVE]", "")
            name = name.strip()

            entity = make_entity_dict(name=name, entity_type="government_organisation")
            self.data.append(entity)

    def save(self):
        """Save the entities to csv"""
        entities = pandas.DataFrame(self.data)
        entities.to_csv(self.output_path, index_label="id")
        self.logger.info("Initial custom data saved: {}".format(self.output_path))
