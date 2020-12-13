"""
Module for relationships
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from ..text import eval_string_as_list
from ..utils import colorize, find_organisation_by_name
from ..constants import ENTITY_TEMPLATE


class BaseRelationship:
    """Base relationship class"""

    NER_TYPES = ["ORG"]
    EXCLUDE_NER_MATCHES = ["trustee"]
    ACCEPTED_SINGLE_MATCHES = ["union", "pollster", "media"]

    def __init__(
        self,
        index,
        relationship,
        entities,
        nlp,
        companies_house_apikey,
        opencorporates_apikey,
        prompt,
        logger,
        parent,
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
        self.prompt = prompt
        self.logger = logger
        self.parent = parent

        self.relationship_type = relationship["relationship_type"]
        self.source = relationship["source"]
        self.target = relationship["target"]
        self.text = relationship["text"]
        self.date = None
        self.amount = None

        self.extracted_entities = []
        self.extracted_custom_entities = []

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
        amounts = []
        for entity in entities:
            if entity[1] in ["MONEY"]:
                pounds = entity[0].split(".")[0]
                amounts.append(re.sub("[^0-9]", "", pounds))
        if amounts:
            return max(amounts)
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

    def _query_nlp_entities(self, text):
        """"""
        self.logger.debug("NLP Query: {}".format(self.relationship["text"]))
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        entity_names = []

        for entity in entities:
            if entity[1] in self.NER_TYPES:
                entity_name = entity[0]
                if entity_name.lower() not in self.EXCLUDE_NER_MATCHES:
                    entity_names.append(entity_name)

        new_entities = []
        for entity_name in entity_names:
            self.logger.debug("NLP Entity: {}".format(entity_name))
            (organisation_name, organisation_registration) = find_organisation_by_name(
                entity_name, self.companies_house_apikey, self.logger
            )

            if organisation_name:

                print("TEXT: {}".format(self.relationship["text"]))
                print("ENT : {}".format(entity_name))
                print(
                    "ORG : {} ({})".format(organisation_name, organisation_registration)
                )

                accept = input("ACCEPT ENTITY ? ")
                if not "y" in accept.lower():
                    continue

                entity_type = input("ENTITY TYPE (company): ")
                if not entity_type:
                    entity_type = "company"

                entity = self.make_entity_dict(
                    entity_type=entity_type,
                    name=organisation_name,
                    company_registration=organisation_registration,
                    aliases=";".join(list(set([text, organisation_name]))),
                )
                new_entities.append(entity)
        return new_entities


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

    def check_aliases(self, entity_types, text=None):
        """Check entity aliases for occurances of query string"""
        if not text:
            text = self.relationship["text"]
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

    def query_nlp_entities(self):
        """"""
        self.logger.debug("NLP Query: {}".format(self.relationship["text"]))
        return self._query_nlp_entities(self.text)

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

    def query_nlp_entities(self):
        """"""
        self.logger.debug("NLP Query: {}".format(self.relationship["text"]))
        return self._query_nlp_entities(self.text["name"])

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

    def find_person_entity(self, name):
        result = self.nlp(name)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["PERSON"]:
                return entity[0].title()


def get_relationship_solver(*args, **kwargs):
    """Utility function to get correct relationship solver object"""

    relationship_type = kwargs["relationship"]["relationship_type"]
    if not relationship_type:
        return None

    elif relationship_type == "member_of":
        from .membership import Membership

        return Membership(*args, **kwargs)

    elif relationship_type == "related_to":
        from .relation import Relation

        return Relation(*args, **kwargs)

    elif relationship_type == "owner_of":
        from .property import PropertyOwner

        return PropertyOwner(*args, **kwargs)

    elif relationship_type == "significant_control_of":
        from .significant import SignificationControl

        return SignificationControl(*args, **kwargs)

    elif relationship_type == "director_of":
        from .director import Directorship

        return Directorship(*args, **kwargs)

    elif relationship_type == "shareholder_of":
        from .shareholder import Shareholder

        return Shareholder(*args, **kwargs)

    elif relationship_type == "miscellaneous":
        from .miscellaneous import Miscellaneous

        return Miscellaneous(*args, **kwargs)

    elif relationship_type == "sponsored_by":
        from .sponsor import Sponsorship

        return Sponsorship(*args, **kwargs)

    elif relationship_type == "donations_from":
        from .donation import Donation

        return Donation(*args, **kwargs)

    elif relationship_type == "gifts_from":
        from .gift import Gift

        return Gift(*args, **kwargs)

    elif relationship_type == "visited":
        from .visit import Visit

        return Visit(*args, **kwargs)

    elif relationship_type == "employed_by":
        from .employment import Employment

        return Employment(*args, **kwargs)

    return None
