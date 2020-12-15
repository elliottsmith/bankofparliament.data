"""
Module for employment relationship
"""
# -*- coding: utf-8 -*-
# sys libs
import re

# local libs
from .base_relationships import TextRelationship
from ..text import (
    strip_category_text,
    strip_registered_text,
    strip_positions_text,
    strip_from_dates_text,
    strip_parenthesis_text,
)
from ..utils import find_organisation_by_name, colorize
from ..patterns import RECURRING_INDICATORS, SINGLE_INDICATORS
from ..constants import ENTITY_TYPES


class Employment(TextRelationship):

    TARGET_ENTITY_TYPE = "company"
    ALIAS_ENTITY_TYPES = ENTITY_TYPES

    SPLITTERS = ["speaker", "engagement", "speaking"]
    STARTERS = ["and ", ",", "of ", "in ", "group"]
    ENDERS = ["."]
    REPLACE = [("  ", " "), (" & ", " and ")]

    recurring_payment_regex = re.compile(
        r"({}).+".format("|".join(RECURRING_INDICATORS).lower())
    )
    single_payment_regex = re.compile(
        r"({}).+".format("|".join(SINGLE_INDICATORS).lower())
    )

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text
        text = strip_category_text(text)
        text = strip_registered_text(text)
        text = strip_from_dates_text(text)
        text = strip_parenthesis_text(text)

        text = self.strip_startwswith(text)
        text = self.strip_endswith(text)
        text = self.run_replace(text)
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

        (organisation_name, organisation_registration) = find_organisation_by_name(
            self.text, self.companies_house_apikey, self.logger
        )

        if organisation_name:
            entity = self.make_entity_dict(
                entity_type=self.TARGET_ENTITY_TYPE,
                name=organisation_name,
                company_registration=organisation_registration,
                aliases=";".join(list(set([self.text, organisation_name]))),
            )
            self.extracted_entities.append(entity)

        if not organisation_name:
            alias = self.check_aliases(
                entity_types=self.ALIAS_ENTITY_TYPES,
                prefered_entity_types=["company", "pollster"],
            )
            if alias:
                filt = self.entities["name"].str.lower() == alias.lower()
                match = self.entities.loc[filt]
                alias_type = match.iloc[0]["entity_type"]

                entity = self.make_entity_dict(
                    entity_type=alias_type,
                    name=alias,
                    aliases=";".join([alias]),
                )
                organisation_name = alias
                self.extracted_entities.append(entity)

        # no organisation in text
        # no alias found
        if not organisation_name and self.amount:

            # search for single payment
            if self.single_payment_regex.search(self.relationship["text"].lower()):

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

                        entity = self.make_entity_dict(
                            entity_type=entity_type,
                            name=rel["target"],
                            aliases=";".join([rel["target"]]),
                        )
                        organisation_name = rel["target"]
                        self.extracted_entities.append(entity)
                        break

        if not organisation_name:
            filt = self.entities["entity_type"] == "profession"
            professions = self.entities.loc[filt]

            for (_index, row) in professions.iterrows():
                if row["name"].lower() in self.text.lower():
                    entity = self.make_entity_dict(
                        entity_type="profession",
                        name=row["name"],
                        aliases=";".join([row["name"]]),
                    )
                    organisation_name = row["name"]
                    self.extracted_entities.append(entity)
                    break

                for alias in row["aliases"].split(";"):
                    if alias.lower() in self.text.lower():
                        entity = self.make_entity_dict(
                            entity_type="profession",
                            name=row["name"],
                            aliases=";".join([row["name"]]),
                        )
                        organisation_name = row["name"]
                        self.extracted_entities.append(entity)
                        break
