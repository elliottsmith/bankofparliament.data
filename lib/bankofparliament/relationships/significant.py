"""
Module for significant relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .base_relationships import TextRelationship
from ..utils import find_organisation_by_name
from ..patterns import IN_PARENTHESIS
from ..constants import OTHER_ENTITIES


class SignificationControl(TextRelationship):
    """Signification control relationship solver"""

    NER_TYPES = ["ORG"]
    ALIAS_ENTITY_TYPES = OTHER_ENTITIES

    def cleanup(self):
        """Clean the text prior to solving"""
        text = self.text

        regex_pattern = ""
        for item in IN_PARENTHESIS:
            regex_pattern += r"\(.*{}.*\)|".format(item)
        regex_pattern = "({})".format(regex_pattern[:-1])

        match = re.search(regex_pattern, text)
        if match:
            groups = match.groups()
            for grp in groups:
                text = text.replace(grp, "")

        text = self.run_replace(text)
        self.text = text

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        (organisation_name, organisation_registration) = find_organisation_by_name(
            self.text, self.companies_house_apikey, self.logger
        )

        if organisation_name:
            entity = self.make_entity_dict(
                entity_type="company",
                name=organisation_name,
                company_registration=organisation_registration,
                aliases=";".join(list(set([self.text, organisation_name]))),
            )
            self.extracted_entities.append(entity)

        if not organisation_name:
            alias = self.check_aliases(entity_types=self.ALIAS_ENTITY_TYPES)
            if alias:
                entity = self.make_entity_dict(
                    entity_type="company",
                    name=alias,
                    aliases=";".join([alias]),
                )
                organisation_name = alias
                self.extracted_entities.append(entity)
