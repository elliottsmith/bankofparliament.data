"""
Module for relationships
"""
# -*- coding: utf-8 -*-

# local libs
from .base import BaseRelationship
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

    def split(self, text, index=0):
        """Split text by values"""
        for splitter in sorted(self.SPLITTERS, key=len, reverse=True):
            if splitter in text:
                text = text.split(splitter)[index]
        return text.strip()

    def strip_startwswith(self, text):
        """Strip values from the start of text"""
        for starter in sorted(self.STARTERS, key=len, reverse=True):
            starter = "{} ".format(starter)
            if text.startswith(starter):
                text = text[len(starter) :]
        return text.strip()

    def strip_endswith(self, text):
        """Strip vaules from end of text"""
        for ender in sorted(self.ENDERS, key=len, reverse=True):
            ender = " {}".format(ender)
            if text.endswith(ender):
                text = text[: -len(ender)]
        return text.strip()

    def run_replace(self, text):
        """Replace a text value with another"""
        for (_from, _to) in self.REPLACE:
            text = text.replace(_from, _to)
        return text.strip()


class CompoundRelationship(BaseRelationship):
    """Compound relationship class - forms a dict like structure"""

    NER_TYPES = []
    ALIAS_ENTITY_TYPES = []

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

    def get_entity_type_from_status(self):
        """Find the entity from the status key"""
        if (
            "individual" in self.text["status"].lower()
            or "private" in self.text["status"].lower()
        ):
            return "person"

        if "charity" in self.text["status"].lower():
            return "charity"

        if "trade union" in self.text["status"].lower():
            return "union"

        if (
            "society" in self.text["status"].lower()
            or "association" in self.text["status"].lower()
        ):
            return "association"

        if (
            "trust" in self.text["status"].lower()
            or "other" in self.text["status"].lower()
        ):
            return "miscellaneous"

        if (
            "company" in self.text["status"].lower()
            or "limited liability" in self.text["status"].lower()
        ):
            return "company"

        return None
