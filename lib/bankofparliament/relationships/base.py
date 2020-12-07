"""
Module for relationships
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from ..text import eval_string_as_list
from ..utils import colorize
from ..constants import ENTITY_TEMPLATE


class BaseRelationship:
    """Base relationship class"""

    def __init__(
        self,
        index,
        relationship,
        entities,
        nlp,
        companies_house_apikey,
        opencorporates_apikey,
        logger,
    ):
        """
        Relationship - pandas DataFrame
        """
        self.index = index
        self.relationship = relationship
        self.entities = entities
        self.nlp = nlp
        self.companies_house_apikey = companies_house_apikey
        self.opencorporates_apikey = opencorporates_apikey
        self.logger = logger

        self.relationship_type = relationship["relationship_type"]
        self.source = relationship["source"]
        self.target = relationship["target"]
        self.text = relationship["text"]
        self.date = None
        self.amount = None

        self.extracted_entities = []

        self.evaluate()
        self.cleanup()

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, source):
        self._source = source

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, target):
        self._target = target

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, date):
        self._date = date

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, amount):
        self._amount = amount

    @property
    def relationship_type(self):
        return self._relationship_type

    @relationship_type.setter
    def relationship_type(self, relationship_type):
        self._relationship_type = relationship_type

    def evaluate(self):
        """Evaluate the relationship text"""

    def cleanup(self):
        """
        Clean up self.text prior to entity extraction
        """

    def solve(self):
        """
        Find entity in self.text
        """

    def update_relationship(self):
        """
        Update the relationship with extracted info
        """
        self.relationship["target"] = self.target
        self.relationship["date"] = self.date
        self.relationship["amount"] = self.amount

        if self.target != "UNKNOWN":
            self.logger.info(
                "[{:05d}] Found: {} [Query: {}]".format(
                    self.index,
                    colorize(self.target, "yellow"),
                    colorize(self.text, "light blue"),
                )
            )
        else:
            self.logger.info(
                "[{:05d}] Not Found: {} [Query: {}]".format(
                    self.index,
                    colorize(self.target, "light red"),
                    colorize(self.text, "light blue"),
                )
            )

    def extract_date_from_text(self, text):
        """Extract date from text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["DATE"]:
                return entity[0]
        return None

    def extract_amount_from_text(self, text):
        """Extract monetary amount from text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["MONEY"]:
                pounds = entity[0].split(".")[0]
                return re.sub("[^0-9]", "", pounds)
        return 0

    def make_entity_dict(self, **kwargs):
        """Add entity data"""
        data = dict.fromkeys(ENTITY_TEMPLATE, "N/A")
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value if value else "N/A"
            else:
                self.logger.debug("Key not found in template: {}".format(key))
        return data


class TextRelationship(BaseRelationship):
    """Text relationship class - single line of text"""

    def evaluate(self):
        """Evaluate as string"""
        self.text = eval_string_as_list(self.relationship["text"])[0]

    def check_aliases(self, entity_types):
        """Check entity aliases for occurances of query string"""
        dataframe = self.entities
        filt = dataframe["entity_type"].isin(entity_types)
        dataframe = dataframe[filt]

        for name, aliases in zip(dataframe["name"], dataframe["aliases"]):
            for alias in aliases.split(";"):
                if alias in self.text:
                    self.logger.info(
                        "Alias Found: {}".format(colorize(name, "magenta"))
                    )
                    return name
        return None


class CompoundRelationship(BaseRelationship):
    """Compound relationship class - forms a dict like structure"""

    def evaluate(self):
        """Find key/value info from list of texts"""

        data = dict.fromkeys(
            ["name", "amount", "status", "address", "date", "destination", "purpose"]
        )

        for line in eval_string_as_list(self.relationship["text"]):
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

        self.text = data


def get_relationship_solver(*args, **kwargs):
    """Utility function to get correct relationship solver object"""
    relationship_type = kwargs["relationship"]["relationship_type"]

    if relationship_type == "shareholder_of":
        from .shareholder import Shareholder
        return Shareholder(*args, **kwargs)

    # elif relationship_type == "member_of":
    #     from .membership import Membership
    #     return Membership(*args, **kwargs)

    # elif relationship_type == "significant_control_of":
    #     from .significant import SignificationControl
    #     return SignificationControl(*args, **kwargs)

    # elif relationship_type == "director_of":
    #     from .director import Directorship
    #     return Directorship(id, relationship, entities)

    # elif relationship_type == "related_to":
    #     from .relation import Relation
    #     return Relation(id, relationship, entities)

    # elif relationship_type == "owner_of":
    #     from .property import PropertyOwner
    #     return PropertyOwner(id, relationship, entities)

    # elif relationship_type == "sponsored_by":
    #     from .sponsor import Sponsorship
    #     return Sponsorship(id, relationship, entities)

    # elif relationship_type == "donations_from":
    #     from .donation import Donation
    #     return Donation(id, relationship, entities)

    # elif relationship_type == "gifts_from":
    #     from .gift import Gift
    #     return Gift(id, relationship, entities)

    # elif relationship_type == "visited":
    #     from .visit import Visit
    #     return Visit(id, relationship, entities)

    # elif relationship_type == "employed_by":
    #     from .employment import Employment
    #     return Employment(id, relationship, entities)

    # elif relationship_type == "miscellaneous":
    #     from .miscellaneous import Miscellaneous
    #     return Miscellaneous(id, relationship, entities)

    return None
