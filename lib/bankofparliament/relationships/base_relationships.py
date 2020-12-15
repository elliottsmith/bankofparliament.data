"""
Module for relationships
"""
# -*- coding: utf-8 -*-

# local libs
from .base import BaseRelationship
from ..utils import colorize
from ..text import eval_string_as_list

class TextRelationship(BaseRelationship):
    """Text relationship class - single line of text"""

    SPLITTERS = []
    STARTERS = []
    ENDERS = []
    REPLACE = [("  ", " "), (" & ", " and ")]
    NER_TYPES = []
    ALIAS_ENTITY_TYPES = []

    def evaluate(self):
        """Evaluate as string"""
        self.text = eval_string_as_list(self.relationship["text"])[0]

    def check_aliases(self, entity_types, prefered_entity_types=[], text=None):
        """Check entity aliases for occurances of query string"""
        if not text:
            text = self.relationship["text"]
        dataframe = self.entities
        filt = dataframe["entity_type"].isin(entity_types)
        dataframe = dataframe[filt]

        _aliases = []
        for name, aliases, etype in zip(
            dataframe["name"], dataframe["aliases"], dataframe["entity_type"]
        ):
            for alias in aliases.split(";"):
                if len(alias.split()) > 1 or etype in self.ACCEPTED_SINGLE_MATCHES:
                    clean_alias = "{}".format(alias.strip().lower())
                    if clean_alias in text.lower():
                        self.logger.debug(
                            "Alias Found: {}".format(colorize(name, "magenta"))
                        )
                        if prefered_entity_types:
                            _aliases.append((etype, name.upper()))
                        else:
                            return name.upper()

        if prefered_entity_types and _aliases:
            best_match = None
            for (_alias_type, _alias_name) in _aliases:
                if _alias_type in prefered_entity_types:
                    best_match = _alias_name
            if best_match:
                return best_match
            return _aliases[0][1]

        return None

    def split(self, text, index=0):
        """"""
        for splitter in sorted(self.SPLITTERS, key=len, reverse=True):
            if splitter in text:
                text = text.split(splitter)[index]
        return text.strip()

    def strip_startwswith(self, text):
        """"""
        for starter in sorted(self.STARTERS, key=len, reverse=True):
            starter = "{} ".format(starter)
            if text.startswith(starter):
                text = text[len(starter) :]
        return text.strip()

    def strip_endswith(self, text):
        """"""
        for ender in sorted(self.ENDERS, key=len, reverse=True):
            ender = " {}".format(ender)
            if text.endswith(ender):
                text = text[: -len(ender)]
        return text.strip()

    def run_replace(self, text):
        """"""
        for (_from, _to) in self.REPLACE:
            text = text.replace(_from, _to)
        return text.strip()


class CompoundRelationship(BaseRelationship):
    """Compound relationship class - forms a dict like structure"""

    def evaluate(self):
        """Find key/value info from list of texts"""
        lines = eval_string_as_list(self.relationship["text"])
        if len(lines) > 1:

            data = dict.fromkeys(
                [
                    "name",
                    "amount",
                    "status",
                    "address",
                    "date",
                    "destination",
                    "purpose",
                ]
            )

            for line in lines:
                if ":" in line:
                    splits = line.split(":")
                    key = splits[0].strip()
                    value = splits[-1].strip()

                    if "name" in key.lower():
                        data["name"] = value

                    elif "amount" in key.lower() or "value" in key.lower():
                        data["amount"] = value

                    elif "status" in key.lower():
                        data["status"] = value

                    elif "address" in key.lower():
                        data["address"] = value

                    elif "destination" in key.lower():
                        data["destination"] = value

                    elif "purpose" in key.lower():
                        data["purpose"] = value

                if "registered" in line.lower():
                    data["date"] = line
        else:
            data = dict.fromkeys(
                [
                    "name",
                    "amount",
                    "status",
                    "address",
                    "date",
                    "destination",
                    "purpose",
                ],
                lines[0],
            )

        self.text = data

    def check_aliases(self, entity_types, text=None):
        """Check entity aliases for occurances of query string"""
        if not text:
            text = self.text["name"]

        dataframe = self.entities
        filt = dataframe["entity_type"].isin(entity_types)
        dataframe = dataframe[filt]

        for name, aliases, etype in zip(
            dataframe["name"], dataframe["aliases"], dataframe["entity_type"]
        ):
            for alias in aliases.split(";"):
                if len(alias.split()) > 1 or etype in self.ACCEPTED_SINGLE_MATCHES:
                    clean_alias = "{}".format(alias.strip().lower())
                    if clean_alias in text.lower():
                        self.logger.debug(
                            "Alias Found: {}".format(colorize(name, "magenta"))
                        )
                        return name.upper()

        return None

    def get_entity_type_from_status(self):
        """"""
        if (
            "individual" in self.text["status"].lower()
            or "private" in self.text["status"].lower()
        ):
            return "person"

        elif "charity" in self.text["status"].lower():
            return "charity"

        elif "trade union" in self.text["status"].lower():
            return "union"

        elif (
            "society" in self.text["status"].lower()
            or "association" in self.text["status"].lower()
        ):
            return "association"

        elif (
            "trust" in self.text["status"].lower()
            or "other" in self.text["status"].lower()
        ):
            return "miscellaneous"

        elif (
            "company" in self.text["status"].lower()
            or "limited liability" in self.text["status"].lower()
        ):
            return "company"

        return None
