"""
Module for misc relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .relationships import TextRelationship
from ..text import (
    strip_category_text,
    strip_registered_text,
    strip_positions_text,
    strip_from_dates_text,
    strip_parenthesis_text,
    strip_punctuation,
    strip_address_text,
    strip_dates_text,
)
from ..constants import ENTITY_TYPES
from ..patterns import (
    UNIVERSITY_IDENTIFIERS,
    EDUCATION_IDENTIFIERS,
    CHARITY_IDENTIFIERS,
    LOCAL_GOVERNMENT_IDENTIFIERS,
    HEALTH_IDENTIFIERS,
    COMPANY_IDENTIFIERS,
    POSITIONS,
)
from ..utils import colorize, make_entity_dict


class Miscellaneous(TextRelationship):
    """Miscellaneous relationship solver"""

    SPLITTERS = ["trading as ", "investee companies", ";"]
    STARTERS = ["and", "of", "of the", "member of the"]
    ENDERS = [".", "board", "committee"]
    REPLACE = [("  ", " "), ("unpaid", "")]
    NER_TYPES = ["ORG", "PERSON"]
    ALIAS_ENTITY_TYPES = ENTITY_TYPES
    PREFERRED_ALIAS_ENTITY_TYPES = ["company", "pollster"]

    IDENTIFIER_TYPES = [
        "university",
        "education",
        "charity",
        "local_authority",
        "health",
        "company",
    ]

    IDENTIFIERS = [
        UNIVERSITY_IDENTIFIERS,
        EDUCATION_IDENTIFIERS,
        CHARITY_IDENTIFIERS,
        LOCAL_GOVERNMENT_IDENTIFIERS,
        HEALTH_IDENTIFIERS,
        COMPANY_IDENTIFIERS,
    ]

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)
        text = strip_positions_text(text)
        text = strip_from_dates_text(text)
        text = strip_parenthesis_text(text)
        text = strip_address_text(text)
        text = strip_dates_text(self.nlp, text)

        text = self.split(text)
        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)
        text = self.run_replace(text)
        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)

        # build texts to query
        nlp_names = self.get_nlp_entities_from_text(
            text=self.text, entity_types=["ORG", "PERSON"]
        )

        # clean name
        names_to_try = [text]

        # nlp names
        for nlp in nlp_names:
            if (
                not nlp in POSITIONS
                and len(nlp.split()) > 1
                and nlp.lower() not in self.EXCLUDE_FROM_NLP
            ):
                names_to_try.append(strip_punctuation(nlp.lower()))
                names_to_try.append(nlp.lower())

        names_to_try = list(set(names_to_try))
        self.names_to_try = names_to_try

        # guess the most apporopiate entity type for query
        _guess_types = []
        for (_type, _identifier) in zip(self.IDENTIFIER_TYPES, self.IDENTIFIERS):
            for _id in _identifier:
                if _id.lower() in self.relationship["text"].lower():
                    _guess_types.append(_type)
        self.guess_types = list(set(_guess_types))

        # set the cleaned name as text
        self.text = text
        self.logger.debug("Guesses: {}".format(self.guess_types))
        self.logger.debug("Names: {}".format(self.names_to_try))

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        # check the raw text against all alias entities
        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        # for every guess type, do a targeted reconcile query, per name_to_try
        for guess in self.guess_types:
            for name in self.names_to_try:
                if guess == "company":
                    entity = self.find_company_from_text(text=name)
                elif guess == "university":
                    entity = self.find_university_from_text(text=name)
                elif guess == "education":
                    entity = self.find_education_from_text(text=name)
                elif guess == "health":
                    entity = self.find_health_from_text(text=name)
                elif guess == "charity":
                    entity = self.find_charity_from_text(text=name)
                elif guess == "local_authority":
                    entity = self.find_local_authority_from_text(text=name)
                else:
                    entity = None

                if entity:
                    self.extracted_entities.append(entity)
                    return

        # do a much wider search, across all jurisdictions for both
        # corporates and charities, schools etc
        for name in self.names_to_try:
            if name.lower() not in self.EXCLUDE_FROM_SEARCHING:
                entity = self.find_organisation_from_text(text=name)
                if entity:
                    self.extracted_entities.append(entity)
                    return

        # profession
        entity = self.find_profession_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        # property
        entity = self.find_property_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return
