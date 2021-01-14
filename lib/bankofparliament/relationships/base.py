"""
Module for relationships
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from ..utils import (
    colorize,
    make_entity_dict,
    findcorporate_by_name,
    findthatcharity_by_name,
    find_organisation_by_name,
    find_organisation_by_number,
)
from ..patterns import RECURRING_INDICATORS, SINGLE_INDICATORS
from ..text import extract_company_registration_number_from_text, eval_string_as_list


class BaseRelationship:
    """Base relationship class"""

    ALIAS_ENTITY_TYPES = []
    PREFERRED_ALIAS_ENTITY_TYPES = []

    NER_TYPES = []
    EXCLUDE_NER_MATCHES = ["trustee"]
    ACCEPTED_SINGLE_MATCHES = [
        "union",
        "pollster",
        "media",
        "government_organisation",
        "property",
    ]
    EXCLUDE_FROM_NLP = [
        "house limited",
        "group limited",
        "house ltd",
        "bank street",
        "county hall",
        "carmelite house",
        "steering committee",
    ]
    EXCLUDE_FROM_SEARCHING = ["solicitor"]

    recurring_payment_regex = re.compile(
        r"({}).+".format("|".join(RECURRING_INDICATORS).lower())
    )
    single_payment_regex = re.compile(
        r"({}).+".format("|".join(SINGLE_INDICATORS).lower())
    )

    def __init__(
        self,
        index,
        relationship,
        entities,
        nlp,
        companies_house_apikey,
        prompt,
        logger,
        parent,
    ):
        """
        Relationship base class
        """
        self.index = index
        self.relationship = relationship
        self.entities = entities
        self.nlp = nlp
        self.companies_house_apikey = companies_house_apikey
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
            elif entity[1] in ["CARDINAL"]:
                if "£{}".format(entity[0]) in text:
                    pounds = entity[0].split(".")[0]
                    amounts.append(re.sub("[^0-9]", "", pounds))
        if amounts:
            return max(amounts)

        match = re.search(r"(£[0-9,.]+)|([0-9]+\.[0-9][0-9])", text)
        if match:
            _amount = match.group().split(".")[0]
            _amount = re.sub("[^0-9]", "", _amount)
            return _amount
        return 0

    def find_single_payment_from_text(self, text):
        """Find a single payment within text"""
        if self.amount:
            # search for single payment
            if self.single_payment_regex.search(text.lower()):

                sources_relationships = self.parent.get_sibling_relationships_by_type(
                    self.relationship["source"], self.relationship["relationship_type"]
                )

                for (_index, rel) in sources_relationships.iterrows():
                    if rel["target"] != "UNKNOWN" and rel["amount"] == "recurring":
                        self.logger.debug(
                            "{}: {}".format(
                                colorize("Recurring payment used", "light blue"),
                                rel["target"],
                            )
                        )

                        filt = (
                            self.entities["name"].str.lower() == rel["target"].lower()
                        )
                        match = self.entities.loc[filt]
                        entity_type = match.iloc[0]["entity_type"]

                        entity = make_entity_dict(
                            entity_type=entity_type,
                            name=rel["target"],
                            aliases=[rel["target"]],
                        )
                        self.logger.debug(
                            "Single Payment Found: {}".format(
                                colorize(rel["target"], "magenta")
                            )
                        )
                        return entity
        return None

    def find_profession_from_text(self, text):
        """Find a profession within text"""
        filt = self.entities["entity_type"] == "profession"
        professions = self.entities.loc[filt]

        for (_index, row) in professions.iterrows():
            if row["name"].lower() in text.lower():
                entity = make_entity_dict(
                    entity_type="profession",
                    name=row["name"],
                    aliases=[row["name"]],
                )
                self.logger.debug(
                    "Profession Found: {}".format(colorize(row["name"], "magenta"))
                )
                return entity

            for alias in row["aliases"].split(";"):
                if alias.lower() in text.lower():
                    entity = make_entity_dict(
                        entity_type="profession",
                        name=row["name"],
                        aliases=[row["name"]],
                    )
                    self.logger.debug(
                        "Profession Found: {}".format(colorize(row["name"], "magenta"))
                    )
                    return entity
        return None

    def find_property_from_text(self, text):
        """Find a property within text"""
        filt = self.entities["entity_type"] == "property"
        properties = self.entities.loc[filt]

        for (_index, row) in properties.iterrows():
            if row["name"].lower() in text.lower():
                entity = make_entity_dict(
                    entity_type="property",
                    name=row["name"],
                    aliases=[row["name"]],
                )
                self.logger.debug(
                    "Property Found: {}".format(colorize(row["name"], "magenta"))
                )
                return entity

            for alias in row["aliases"].split(";"):
                if alias.lower() in text.lower():
                    entity = make_entity_dict(
                        entity_type="property",
                        name=row["name"],
                        aliases=[row["name"]],
                    )
                    self.logger.debug(
                        "Property Found: {}".format(colorize(row["name"], "magenta"))
                    )
                    return entity
        return None

    def find_ner_type_from_text(self, text, target_entity_type):
        """Find NER types within text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]

        for entity in entities:
            if entity[1] in self.NER_TYPES:
                entity_name = entity[0]

                if len(entity_name.split()) > 1:
                    entity = make_entity_dict(
                        entity_type=target_entity_type,
                        name=entity_name,
                        aliases=[entity_name],
                    )
                    self.logger.debug(
                        "Entity Found: {}".format(colorize(entity_name, "magenta"))
                    )
                    return entity
        return None

    def find_organisation_from_text(self, text):
        """Find any organistation from text"""

        try:
            text = eval_string_as_list(text)[0]
        except:
            text = text

        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = find_organisation_by_name(text, self.companies_house_apikey, self.logger)

        if organisation_name:

            if entity_type == "company":
                opencorporates_registration = organisation_registration
                findthatcharity_registration = None
            else:
                opencorporates_registration = None
                findthatcharity_registration = organisation_registration

            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                opencorporates_registration=opencorporates_registration,
                findthatcharity_registration=findthatcharity_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Organisation Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_company_from_text(self, text):
        """Find company from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findcorporate_by_name(text, self.logger)

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                opencorporates_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Company Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_charity_from_text(self, text):
        """Find charity from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger, "registered-charity")

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Charity Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_health_from_text(self, text):
        """Find health from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger, "health")

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Health Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_university_from_text(self, text):
        """Find university from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger, "university")

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "University Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_education_from_text(self, text):
        """Find education from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger, "education")

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Education Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_government_organisation_from_text(self, text):
        """Find government organisation from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger, "government-organisation")

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Government Organisation Found: {}".format(
                    colorize(organisation_name, "magenta")
                )
            )
            return entity
        return None

    def find_local_authority_from_text(self, text):
        """Find local authority from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger, "local_authority")

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Local Authority Found: {}".format(
                    colorize(organisation_name, "magenta")
                )
            )
            return entity
        return None

    def findthatcharity_from_text(self, text):
        """Find charitable from text"""
        (
            organisation_name,
            organisation_registration,
            entity_type,
        ) = findthatcharity_by_name(text, self.logger)

        if organisation_name:
            entity = make_entity_dict(
                entity_type=entity_type,
                name=organisation_name,
                findthatcharity_registration=organisation_registration,
                aliases=list(set([text, organisation_name])),
            )
            self.logger.debug(
                "Charitable Found: {}".format(colorize(organisation_name, "magenta"))
            )
            return entity
        return None

    def find_organisation_from_number_in_text(self, text):
        """Find organisation from number within text"""
        organisation_registration = extract_company_registration_number_from_text(
            text, self.logger
        )
        if organisation_registration:
            self.logger.debug("Registration: {}".format(organisation_registration))

            organisation_name = find_organisation_by_number(
                self.companies_house_apikey,
                organisation_registration,
                self.logger,
            )
            if organisation_name:
                organisation_registration = "/companies/gb/{}".format(organisation_registration)
                entity = make_entity_dict(
                    entity_type="company",
                    name=organisation_name,
                    opencorporates_registration=organisation_registration,
                    aliases=list(set([text, organisation_name])),
                )
                self.logger.debug(
                    "Company Found: {}".format(colorize(organisation_name, "magenta"))
                )
                return entity
        return None

    def find_alias_from_text(
        self, text, alias_entity_types=None, prefered_entity_types=None
    ):
        """Find alias from text"""
        if text.lower() == "community":
            entity = make_entity_dict(
                entity_type="union",
                name="community union",
                aliases=[text],
            )
            return entity

        alias_entity_types = (
            alias_entity_types if alias_entity_types else self.ALIAS_ENTITY_TYPES
        )
        prefered_entity_types = (
            prefered_entity_types
            if prefered_entity_types
            else self.PREFERRED_ALIAS_ENTITY_TYPES
        )

        alias = self._check_aliases(
            entity_types=alias_entity_types,
            prefered_entity_types=prefered_entity_types,
            text=text,
        )
        if alias:
            filt = self.entities["name"].str.lower() == alias.lower()
            match = self.entities.loc[filt]
            alias_type = match.iloc[0]["entity_type"]

            entity = make_entity_dict(
                entity_type=alias_type,
                name=alias,
                aliases=[alias],
            )
            self.logger.debug("Alias Found: {}".format(colorize(alias, "magenta")))
            return entity
        return None

    def _check_aliases(self, entity_types, prefered_entity_types, text):
        """Check entity aliases for occurances of query string"""
        try:
            text = eval_string_as_list(text)[0].lower()
        except:
            text = text.lower()

        self.logger.debug(
            "Checking Alias: ({}) {} ({})".format(
                text, entity_types, prefered_entity_types
            )
        )
        dataframe = self.entities
        filt = dataframe["entity_type"].isin(entity_types)
        dataframe = dataframe[filt]

        _aliases = []
        for name, aliases, etype in zip(
            dataframe["name"], dataframe["aliases"], dataframe["entity_type"]
        ):
            for alias in aliases.split(";"):
                alias = alias.strip().lower()
                # if len(alias.split()) > 1 or etype in self.ACCEPTED_SINGLE_MATCHES:
                #     pass

                # does the word match exactly
                if text == alias:
                    if prefered_entity_types:
                        _aliases.append((etype, name.upper()))
                    else:
                        return name.upper()

                # does the word exist at the start of the string, with a space following
                start_alias = "{} ".format(alias)
                if text.startswith(start_alias):
                    if prefered_entity_types:
                        _aliases.append((etype, name.upper()))
                    else:
                        return name.upper()

                # does the word exist at the end of the string, precedding with a space
                end_alias = " {}".format(alias)
                if text.endswith(end_alias):
                    if prefered_entity_types:
                        _aliases.append((etype, name.upper()))
                    else:
                        return name.upper()

                in_patterns = [
                    " {} ",
                    " {},",
                    " {}.",
                    " {};",
                    " {}'",
                    " {}’",
                    "{})",
                    "{};",
                    "{}.",
                    "{},",
                    '{}"',
                ]
                # does the pattern exist in the text
                for _pattern in in_patterns:
                    pattern = _pattern.format(alias)
                    if pattern in text:
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

    def get_nlp_entities_from_text(self, text, entity_types=None):
        """"""
        if not entity_types:
            entity_types = self.NER_TYPES

        result = self.nlp(text=text)
        entities = [(X.text, X.label_) for X in result.ents]
        nlp_names = []
        for entity in entities:
            if entity[1] in entity_types:
                _name = entity[0]
                if len(_name.split()) > 1:
                    nlp_names.append(_name)
        return nlp_names


def get_relationship_solver(*args, **kwargs):
    """Utility function to get correct relationship solver object"""
    relationship_type = kwargs["relationship"]["relationship_type"]
    if not relationship_type:
        return None

    if relationship_type == "constitutional_head_of":
        from .constitutional import Constitutional

        return Constitutional(*args, **kwargs)

    if relationship_type == "member_of":
        from .membership import Membership

        return Membership(*args, **kwargs)

    if relationship_type == "related_to":
        from .relation import Relation

        return Relation(*args, **kwargs)

    if relationship_type == "owner_of":
        from .property import PropertyOwner

        return PropertyOwner(*args, **kwargs)

    if relationship_type == "significant_control_of":
        from .significant import SignificationControl

        return SignificationControl(*args, **kwargs)

    if relationship_type == "director_of":
        from .director import Directorship

        return Directorship(*args, **kwargs)

    if relationship_type == "shareholder_of":
        from .shareholder import Shareholder

        return Shareholder(*args, **kwargs)

    if relationship_type == "miscellaneous":
        from .miscellaneous import Miscellaneous

        return Miscellaneous(*args, **kwargs)

    if relationship_type == "sponsored_by":
        from .sponsor import Sponsorship

        return Sponsorship(*args, **kwargs)

    if relationship_type == "donation_from":
        from .donation import Donation

        return Donation(*args, **kwargs)

    if relationship_type == "gift_from":
        from .gift import Gift

        return Gift(*args, **kwargs)

    if relationship_type == "visited":
        from .visit import Visit

        return Visit(*args, **kwargs)

    if relationship_type == "employed_by":
        from .employment import Employment

        return Employment(*args, **kwargs)

    if relationship_type == "advisor_to":
        from .advisor import Advisor

        return Advisor(*args, **kwargs)

    return None
