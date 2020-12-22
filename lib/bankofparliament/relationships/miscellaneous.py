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
)
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
)
from ..utils import make_entity_dict


class Miscellaneous(TextRelationship):
    """Miscellaneous relationship solver"""

    SPLITTERS = ["trading as ", "investee companies", ";"]
    STARTERS = ["and", "of", "of the", "member of the"]
    ENDERS = ["."]
    REPLACE = [("  ", " "), (" & ", " and "), ("unpaid", "")]
    NER_TYPES = ["ORG", "PERSON"]
    ALIAS_ENTITY_TYPES = ENTITY_TYPES
    PREFERRED_ALIAS_ENTITY_TYPES = ["company", "pollster"]
    EXCLUDE_FROM_SEARCHING = ["solicitor"]

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)
        text = strip_positions_text(text)
        text = strip_from_dates_text(text)
        text = strip_parenthesis_text(text)

        text = self.split(text)
        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)
        text = self.run_replace(text)
        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)

        self.text = text

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        identifier_types = [
            "university",
            "education",
            "charity",
            "government_organisation",
            "local_authority",
            "health",
            "company",
            "state_power",
            "state_power",
            "state_power",
            "state_power",
            "misc",
        ]

        identifiers = [
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
        ]

        _guess_types = []
        for (_type, _identifier) in zip(identifier_types, identifiers):
            for _id in _identifier:
                if _id.lower() in self.relationship["text"].lower():
                    _guess_types.append(_type)

        guess_types = list(set(_guess_types))
        # print("Guess types: {}".format(guess_types))

        nlp_names = self.get_nlp_entities_from_text(
            text=self.relationship["text"], entity_types=["ORG"]
        )
        nlp_names.insert(0, self.text)
        names_to_try = list(set(nlp_names))
        # print("Nlp names: {}".format(names_to_try))

        for guess in guess_types:

            entity = self.find_alias_from_text(
                text=self.relationship["text"], alias_entity_types=[guess]
            )
            if entity:
                self.extracted_entities.append(entity)
                return

            if guess == "company":
                for name in names_to_try:
                    entity = self.find_company_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "university":
                for name in names_to_try:
                    entity = self.find_university_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "education":
                for name in names_to_try:
                    entity = self.find_education_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "health":
                for name in names_to_try:
                    entity = self.find_health_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "charity":
                for name in names_to_try:
                    entity = self.find_charity_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "government_organisation":
                for name in names_to_try:
                    entity = self.find_government_organisation_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "local_authority":
                for name in names_to_try:
                    entity = self.find_local_authority_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

            if guess == "misc":
                for name in names_to_try:
                    entity = self.findthatcharity_from_text(text=name)
                    if entity:
                        self.extracted_entities.append(entity)
                        return

        entity = self.find_alias_from_text(text=self.relationship["text"])
        if entity:
            self.extracted_entities.append(entity)
            return

        if self.text.lower() not in self.EXCLUDE_FROM_SEARCHING:
            for name in names_to_try:
                entity = self.find_organisation_from_text(text=name)
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
