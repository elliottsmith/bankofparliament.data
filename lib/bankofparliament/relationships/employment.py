"""
Module for employment relationship
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
)
from ..utils import colorize, make_entity_dict
from ..constants import ENTITY_TYPES

from ..patterns import (
    UNIVERSITY_IDENTIFIERS,
    EDUCATION_IDENTIFIERS,
    CHARITY_IDENTIFIERS,
    GOVERNMENT_IDENTIFIERS,
    LOCAL_GOVERNMENT_IDENTIFIERS,
    HEALTH_IDENTIFIERS,
    COMPANY_IDENTIFIERS,
    ARMED_FORCES_IDENTIFIERS,
    CHURCH_OF_ENGLAND_IDENTIFIERS,
    JURDICARY_IDENTIFIERS,
    CROWN_IDENTIFIERS,
    MISC_IDENTIFIERS,
    POSITIONS,
)


class Employment(TextRelationship):
    """Employment relationship solver"""

    TARGET_ENTITY_TYPE = "company"
    ALIAS_ENTITY_TYPES = ENTITY_TYPES
    PREFERRED_ALIAS_ENTITY_TYPES = ["company", "pollster"]

    SPLITTERS = ["speaker", "engagement", "speaking"]
    STARTERS = ["and ", ",", "of ", "in ", "group"]
    ENDERS = [".", "board"]
    REPLACE = [("  ", " "), ("unpaid", "")]
    NER_TYPES = ["ORG"]
    EXCLUDE_FROM_SEARCHING = ["solicitor"]
    EXCLUDE_FROM_NLP = ["house limited", "group limited", "house ltd"]

    IDENTIFIER_TYPES = [
        "university",
        "education",
        "charity",
        "local_authority",
        "health",
        "company",
        "government",
        "armed_forces",
        "church",
        "judicary",
        "crown",
        "misc",
    ]

    IDENTIFIERS = [
        UNIVERSITY_IDENTIFIERS,
        EDUCATION_IDENTIFIERS,
        CHARITY_IDENTIFIERS,
        LOCAL_GOVERNMENT_IDENTIFIERS,
        HEALTH_IDENTIFIERS,
        COMPANY_IDENTIFIERS,
        GOVERNMENT_IDENTIFIERS,
        ARMED_FORCES_IDENTIFIERS,
        CHURCH_OF_ENGLAND_IDENTIFIERS,
        JURDICARY_IDENTIFIERS,
        CROWN_IDENTIFIERS,
        MISC_IDENTIFIERS,
    ]

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)
        text = strip_from_dates_text(text)
        text = strip_parenthesis_text(text)
        text = strip_positions_text(text)

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
                names_to_try.append(nlp)

        # original text - last
        names_to_try.append(self.text)
        names_to_try = list(set([strip_punctuation(n.lower()) for n in names_to_try]))
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

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        # recurring payments
        recurring = self.recurring_payment_regex.search(
            self.relationship["text"].lower()
        )
        if recurring:
            self.logger.debug(
                "{}: {}".format(
                    colorize("Recurring payment set", "light blue"),
                    self.relationship["text"],
                )
            )
            self.amount = "recurring"

        if len(self.names_to_try) < 3:
            # no nouns
            entity = self.find_single_payment_from_text(text=self.relationship["text"])
            if entity:
                self.extracted_entities.append(entity)
                return

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        self.logger.debug("Guesses: {}".format(self.guess_types))
        self.logger.debug("Name: {}".format(self.names_to_try))

        for guess in self.guess_types:

            entity = self.find_alias_from_text(
                text=self.relationship["text"], alias_entity_types=[guess]
            )
            if entity:
                self.extracted_entities.append(entity)
                return

            if guess == "company":
                for name in self.names_to_try:
                    entity = self.find_company_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "university":
                for name in self.names_to_try:
                    entity = self.find_university_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "education":
                for name in self.names_to_try:
                    entity = self.find_education_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "health":
                for name in self.names_to_try:
                    entity = self.find_health_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "charity":
                for name in self.names_to_try:
                    entity = self.find_charity_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "government_organisation":
                for name in self.names_to_try:
                    entity = self.find_government_organisation_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "local_authority":
                for name in self.names_to_try:
                    entity = self.find_local_authority_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            # non queryable entities
            if guess in ["armed_forces", "church", "judicary", "crown", "government"]:

                entity_type = "state_power"
                if guess == "armed_forces":
                    organisation_name = "BRITISH ARMED FORCES"
                elif guess == "church":
                    organisation_name = "CHURCH OF ENGLAND"
                elif guess == "judicary":
                    organisation_name = "JUDICARY"
                elif guess == "crown":
                    organisation_name = "THE CROWN"
                elif guess == "government":
                    organisation_name = "HER MAJESTY'S GOVERNMENT"

                entity = make_entity_dict(
                    entity_type=entity_type,
                    name=organisation_name,
                    aliases=list(set([self.text, organisation_name])),
                )
                if entity:
                    self.extracted_entities.append(entity)
                    self.logger.debug(
                        "State Power Found: {}".format(
                            colorize(organisation_name, "magenta")
                        )
                    )
                    return entity

        if self.text.lower() not in self.EXCLUDE_FROM_SEARCHING:
            for name in self.names_to_try:
                entity = self.find_organisation_from_text(text=name)
                if entity:
                    self.extracted_entities.append(entity)
                    return

        entity = self.find_single_payment_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_profession_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        entity = self.find_property_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return
