"""
Module for gift relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .base_relationships import CompoundRelationship
from ..text import extract_company_registration_number_from_text
from ..utils import find_organisation_by_number, find_organisation_by_name
from ..constants import ENTITY_TYPES


class Gift(CompoundRelationship):
    """Gift relationship solver"""

    ALIAS_ENTITY_TYPES = ENTITY_TYPES

    def cleanup(self):
        """Clean the text prior to solving"""
        self.entity_type = self.get_entity_type_from_status()
        self.text["name"] = self.text["name"].replace(" & ", " and ")

        multi_entry_regex = r"\([0-9]+\) ([a-zA-Z ]+)"
        multi_match = re.findall(multi_entry_regex, self.text["name"]) or []
        self._entities = multi_match if multi_match else [self.text["name"]]

    def solve(self):
        """Find entity in text"""
        self.date = self.extract_date_from_text(self.text["date"])
        self.amount = self.extract_amount_from_text(self.text["amount"])

        for entity in self._entities:
            if self.entity_type == "company":

                organisation_name = None
                organisation_registration = (
                    extract_company_registration_number_from_text(
                        self.text["status"], self.logger
                    )
                )
                if organisation_registration:
                    organisation_name = find_organisation_by_number(
                        self.companies_house_apikey,
                        organisation_registration,
                        self.logger,
                    )
                else:
                    (
                        organisation_name,
                        organisation_registration,
                    ) = find_organisation_by_name(
                        self.text["name"], self.companies_house_apikey, self.logger
                    )

                if organisation_name:
                    entity = self.make_entity_dict(
                        entity_type="company",
                        name=organisation_name,
                        company_registration=organisation_registration,
                        aliases=";".join(list(set([entity, organisation_name]))),
                    )
                    self.extracted_entities.append(entity)

                else:
                    alias = self.check_aliases(
                        entity_types=self.ALIAS_ENTITY_TYPES, text=entity
                    )
                    if alias:
                        entity = self.make_entity_dict(
                            entity_type="company",
                            name=alias,
                            aliases=";".join([alias]),
                        )
                        organisation_name = alias
                        self.extracted_entities.append(entity)

            else:
                # trade union etc
                alias = self.check_aliases(
                    entity_types=self.ALIAS_ENTITY_TYPES, text=entity
                )
                if alias:
                    entity = self.make_entity_dict(
                        entity_type=self.entity_type,
                        name=alias,
                        aliases=";".join([alias]),
                    )
                    organisation_name = alias
                    self.extracted_entities.append(entity)
