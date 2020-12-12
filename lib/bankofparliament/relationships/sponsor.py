"""
Module for sponsor relationship
"""
# -*- coding: utf-8 -*-

# local libs
from .base import TextRelationship
from ..utils import find_organisation_by_name
from ..constants import ENTITY_TYPES


class Sponsorship(TextRelationship):
    """Shareholder relationship solver"""

    EXCLUDE = ["house", "parliament", "co-chair", "house of lords"]
    NER_TYPES = ["ORG"]
    ALIAS_ENTITY_TYPES = ENTITY_TYPES

    def solve(self):
        """Find entity in text"""
        entities_found = False
        self.date = self.extract_date_from_text(self.relationship["text"])
        self.amount = self.extract_amount_from_text(self.relationship["text"])

        result = self.nlp(self.text)
        entities = [(X.text, X.label_) for X in result.ents]

        for entity in entities:
            if entity[1] == "PERSON":
                entity_name = entity[0]

                if len(entity_name.split()) > 1:
                    entity = self.make_entity_dict(
                        entity_type="person",
                        name=entity_name,
                        aliases=";".join([entity_name]),
                    )
                    entities_found = True
                    self.extracted_entities.append(entity)

            elif entity[1] == "ORG":
                entity_name = entity[0]

                for starter in ["the "]:
                    if entity_name.lower().startswith(starter):
                        entity_name = entity_name[len(starter) :]
                entity_name = entity_name.strip()

                if not entity_name.lower() in self.EXCLUDE:
                    (
                        organisation_name,
                        organisation_registration,
                    ) = find_organisation_by_name(
                        entity_name, self.companies_house_apikey, self.logger
                    )

                    if organisation_name:
                        entity = self.make_entity_dict(
                            entity_type="company",
                            name=organisation_name,
                            company_registration=organisation_registration,
                            aliases=";".join(
                                list(set([entity_name, organisation_name]))
                            ),
                        )
                        entities_found = True
                        self.extracted_entities.append(entity)

        if not entities_found:
            entity_name = None
            alias = self.check_aliases(entity_types=self.ALIAS_ENTITY_TYPES)
            if alias:
                entity = self.make_entity_dict(
                    entity_type="company",
                    name=alias,
                    aliases=";".join([alias]),
                )
                entity_name = alias
                self.extracted_entities.append(entity)

            alias = self.check_aliases(entity_types=["person"])
            if alias:
                entity = self.make_entity_dict(
                    entity_type="person",
                    name=alias,
                    aliases=";".join([alias]),
                )
                entity_name = alias
                self.extracted_entities.append(entity)

        if not entity_name and self.prompt:
            entities = self.query_nlp_entities()
            self.extracted_custom_entities.extend(entities)
