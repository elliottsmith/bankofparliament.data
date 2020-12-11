"""
Module for gift relationship
"""
# -*- coding: utf-8 -*-

# sys libs
import re

# local libs
from .base import CompoundRelationship
from ..text import extract_company_registration_number_from_text
from ..utils import find_organisation_by_number, find_organisation_by_name


class Gift(CompoundRelationship):
    """Gift relationship solver"""

    ALIAS_ENTITY_TYPES = [
        "company",
        "association",
        "government_body",
        "charity",
        "government",
        "union",
        "education",
        "media",
        "person",
        "miscellaneous",
        "offshore",
        "political",
        "politician",
        "sport",
        "think_lobby",
    ]

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

                if not organisation_name and self.prompt:
                    entities = self.query_nlp_entities()
                    self.extracted_custom_entities.extend(entities)

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

                elif self.prompt:
                    entities = self.query_nlp_entities()
                    self.extracted_custom_entities.extend(entities)

    # entity_type, entity_name, company_registration = None, None, None

    # def cleanup(self):
    #     """"""

    #     self.text["name"] = self.text["name"].replace(" & ", " and ")

    #     # if not "status" in self.text:
    #     #     print("LOOK")
    #     #     print(self.text)

    #     if (
    #         "individual" in self.text["status"].lower()
    #         or "private" in self.text["status"].lower()
    #     ):
    #         # PERSON
    #         # print("Person: {}".format(self.text["name"]))
    #         self.entity_name = self.text["name"]
    #         self.entity_type = "person"

    #     elif "charity" in self.text["status"].lower():
    #         # CHARITY
    #         # print("Charity: {}".format(self.text["name"]))
    #         self.entity_name = self.text["name"]
    #         self.entity_type = "charity"

    #     elif "trade union" in self.text["status"].lower():
    #         # TRADE UNION
    #         # print("Union: {}".format(self.text["name"]))
    #         self.entity_name = self.text["name"]
    #         self.entity_type = "union"

    #     elif (
    #         "society" in self.text["status"].lower()
    #         or "association" in self.text["status"].lower()
    #     ):
    #         # NON REGISTERED ORGANISATION
    #         # print("Assoc: {}".format(self.text["name"]))
    #         self.entity_name = self.text["name"]
    #         self.entity_type = "association"

    #     elif (
    #         "trust" in self.text["status"].lower()
    #         or "other" in self.text["status"].lower()
    #     ):
    #         # NON REGISTERED ORGANISATION
    #         # print("Unreg: {}".format(self.text["name"]))
    #         self.entity_name = self.text["name"]
    #         self.entity_type = "miscellaneous"

    #     elif (
    #         "company" in self.text["status"].lower()
    #         or "limited liability" in self.text["status"].lower()
    #     ):
    #         # COMPANY
    #         # print("Company: {}".format(self.text["name"]))
    #         self.entity_type = "company"

    #         company_registration_number = extract_company_registration_number_from_text(
    #             self.text["status"], self.logger
    #         )
    #         self.entity_name = find_organisation_by_number(
    #             self.companies_house_apikey,
    #             company_registration_number,
    #             self.logger,
    #         )
    #         if self.entity_name:
    #             self.company_registration = company_registration_number

    #     # else:
    #     #     print("Unknown: {}".format(self.text))

    # def solve(self):
    #     """Find entity in text"""

    #     self.date = self.extract_date_from_text(self.text["date"])
    #     self.amount = self.extract_amount_from_text(self.text["amount"])

    #     if self.entity_name:
    #         self.target = self.entity_name
    #         entity = self.make_entity_dict(
    #             entity_type=self.entity_type,
    #             name=self.entity_name,
    #             company_registration=self.company_registration,
    #             aliases=";".join([self.target]),
    #         )
    #         self.extracted_entities.append(entity)

    #     else:
    #         alias = self.check_aliases(
    #             entity_types=[
    #                 "company",
    #                 "association",
    #                 "government_body",
    #                 "person",
    #                 "charity",
    #             ]
    #         )
    #         if alias:
    #             self.target = alias

    #     self.update_relationship()
