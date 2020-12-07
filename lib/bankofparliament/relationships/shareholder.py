"""
Module for shareholder relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .base import TextRelationship
from ..text import (
    strip_category_text,
    strip_registered_text,
    find_text_within_parenthesis_excluding_other_parenthesis,
    has_consecutive_capital_letters_within_parenthesis,
)
from ..patterns import POSITIONS
from ..utils import find_organisation_by_name


class Shareholder(TextRelationship):
    """Shareholder relationship solver"""

    TARGET_ENTITY_TYPE = "company"
    SPLITTERS = [
        "trading as ",
        "investee companies",
        ";",
        ":",
        ", a",
        ", marketing consultancy",
        ", financial services company",
        ", psychology assessment",
        ", tour operator",
        ", shares co-owned",
        ". UK property company",
        ", Sporting Video Company",
        ", management of",
        "family business",
        "in the EdTech space",
        "SIPP",
        "per cent ownership",
        r"% ownership",
    ]
    STARTERS = ["and ", ", ", "of ", "in "]
    ENDERS = ["."]

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)

        # Remove any positions from text, chairman, director etc
        pattern = "{}".format(",? |".join(sorted(POSITIONS, key=len, reverse=True)))
        text = re.sub(pattern, "", text)

        parenthesis_match = find_text_within_parenthesis_excluding_other_parenthesis(
            text
        )
        if parenthesis_match:
            for match in parenthesis_match:
                if not has_consecutive_capital_letters_within_parenthesis(match):
                    text = text.replace(match, "")

        for splitter in self.SPLITTERS:
            if splitter in text:
                text = text.split(splitter)[0]

        from_until_pattern = "(Until [a-zA-Z0-9 ]+,)|(From [a-zA-Z0-9 ]+,)"
        match = re.search(from_until_pattern, text)
        if match:
            grps = match.group()
            text = text.replace(grps, "")

        for starter in self.STARTERS:
            if text.startswith(starter):
                text = text[len(starter) :]
        text = text.strip()

        for ender in self.ENDERS:
            if text.endswith(ender):
                text = text[: -len(ender)]

        text = text.replace("  ", " ")
        text = text.strip()
        self.text = text

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.text)
        self.amount = self.extract_amount_from_text(self.text)

        (organisation_name, organisation_registration) = find_organisation_by_name(
            self.text, self.companies_house_apikey, self.logger
        )

        self.target = organisation_name if organisation_name else "UNKNOWN"
        if organisation_name:
            entity = self.make_entity_dict(
                entity_type=self.TARGET_ENTITY_TYPE,
                name=organisation_name,
                company_registration=organisation_registration,
                aliases=";".join(list(set([self.text, organisation_name]))),
            )
            self.extracted_entities.append(entity)

        else:
            alias = self.check_aliases(entity_types=["company"])
            if alias:
                self.target = alias

        self.update_relationship()
