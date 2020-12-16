"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import time
import shutil

# third party
import pandas
import spacy

# local libs
from .utils import (
    read_csv_as_dataframe,
    colorize,
    find_organisation_by_number,
    find_charity_by_number,
    reconcile_opencorporates_entity_by_id,
)
from .constants import NER_BASE_MODEL, ENTITY_TEMPLATE, RELATIONSHIP_TEMPLATE
from .relationships.base import get_relationship_solver
from .text import get_registration_number_from_link


class NamedEntityExtract:
    """Class to extract entities from raw data"""

    ENTITY_CSV_TEMPLATE = "{}/entities.csv"
    CUSTOM_ENTITY_CSV_TEMPLATE = "{}/custom.csv"
    RELATIONSHIPS_ENTITY_CSV_TEMPLATE = "{}/relationships.csv"

    START = 0
    END = -1

    def __init__(
        self,
        entities,
        custom_entities,
        relationships,
        companies_house_apikey,
        opencorporates_apikey,
        charities_apikey,
        prompt,
        logger,
    ):
        """Read all passed in data files"""
        self._time_start = time.time()
        self.companies_house_apikey = companies_house_apikey
        self.opencorporates_apikey = opencorporates_apikey
        self.charities_apikey = charities_apikey

        self.prompt = prompt
        self.logger = logger
        self.output_dir = os.path.join(os.path.dirname(entities), "extracted")

        # read in data
        _entities = read_csv_as_dataframe(entities)
        _relationships = read_csv_as_dataframe(relationships)
        _custom_entities = read_csv_as_dataframe(custom_entities)

        if not len(_custom_entities):
            _custom_entities = pandas.DataFrame(columns=_entities.columns)

        # dataframes
        self._entities = pandas.concat([_entities, _custom_entities], ignore_index=True)
        self._relationships = _relationships[self.START : self.END]

        # output dataframes
        self._extracted_entities = self._entities
        self._extracted_custom_entities = _custom_entities
        self._extracted_relationships = pandas.DataFrame(
            columns=self._relationships.columns
        )

        # initialise nlp model
        self.logger.debug("Loading NER model: {}".format(NER_BASE_MODEL))
        self.nlp = spacy.load(NER_BASE_MODEL)

        self.processed_relationships = 0
        self.resolved_relationships = 0

    @property
    def entities(self):
        return self._entities

    @property
    def relationships(self):
        return self._relationships

    def execute(self):
        """Execute"""
        self.backup_csv_files()
        self.save_custom()
        self.extract_entities_from_relationships()
        self.save()
        self.log_output()

    def extract_entities_from_relationships(self):
        """Extract entities from the relationships"""
        for (index, relationship) in self.relationships.iterrows():

            if relationship["source"] == "UNKNOWN":
                resolved_source = self.get_missing_source_entity(relationship)
                if resolved_source:
                    relationship["source"] = resolved_source

            # get the solver for the relationship type
            solver = get_relationship_solver(
                index=index,
                relationship=relationship,
                entities=self.entities,
                nlp=self.nlp,
                companies_house_apikey=self.companies_house_apikey,
                opencorporates_apikey=self.opencorporates_apikey,
                prompt=self.prompt,
                logger=self.logger,
                parent=self,
            )

            # solve for entites, add any new ones found
            # for every entity, create a relationship from source
            if solver:
                self.processed_relationships += 1
                solver.solve()

                # check to see if we have extracted entities, if we don't
                # have any, prompt for override if specified
                if not len(
                    solver.extracted_entities + solver.extracted_custom_entities
                ):
                    if self.prompt:
                        manual_entity = self.prompt_manual_input(relationship)
                        if manual_entity:
                            solver.extracted_custom_entities.append(manual_entity)
                        else:
                            self.log_relationship(
                                index, relationship, debug_text=solver.text
                            )
                            continue
                    else:
                        self.log_relationship(
                            index, relationship, debug_text=solver.text
                        )
                        continue

                self.resolved_relationships += 1
                # add all the entities found and a relationship
                for entity in (
                    solver.extracted_entities + solver.extracted_custom_entities
                ):
                    self.add_entity(entity)
                    relationship = self.make_relationship_dict(
                        relationship_type=relationship["relationship_type"],
                        source=relationship["source"],
                        target=entity["name"],
                        date=solver.date,
                        amount=solver.amount,
                        text=relationship["text"],
                        link=relationship["link"],
                    )
                    self.add_relationship(relationship)
                    self.log_relationship(index, relationship)

                # also save out custom entities separately
                for entity in solver.extracted_custom_entities:
                    self.add_custom_entity(entity)
                    self.save_custom()

    def get_missing_source_entity(self, relationship):
        """Find the missing source entity for members relatives"""
        target = relationship["target"]  # this is the member
        target_relations = self.get_sibling_relationships_by_type(target, "related_to")

        for (_index, row) in target_relations.iterrows():
            return row["target"]
        return None

    def get_sibling_relationships_by_type(self, source, relationship_type):
        """Check if entity name already exists"""
        filt = (
            self._extracted_relationships["source"].str.lower() == source.lower()
        ) & (
            self._extracted_relationships["relationship_type"].str.lower()
            == relationship_type.lower()
        )
        relationships = self._extracted_relationships.loc[filt]
        relationships = relationships.reindex(index=relationships.index[::-1])
        return relationships

    def make_entity_dict(self, **kwargs):
        """Add entity data"""
        data = dict.fromkeys(ENTITY_TEMPLATE, "N/A")
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value if value else "N/A"
            else:
                self.logger.debug("Key not found in template: {}".format(key))
        return data

    def make_relationship_dict(self, **kwargs):
        """Add relationship data"""
        data = dict.fromkeys(RELATIONSHIP_TEMPLATE, "N/A")
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value if value else "N/A"
            else:
                self.logger.debug("Key not found in template: {}".format(key))
        return data

    def add_entity(self, entity):
        """Add entity data"""
        entity_name = entity["name"]
        if not self.entity_name_exists(entity_name):
            new_entity = pandas.DataFrame([entity])
            self._entities = pandas.concat(
                [self._entities, new_entity], ignore_index=True
            )
        else:
            filt = self.entities["name"].str.lower() == entity_name.lower()
            existing_entity = self.entities.loc[filt]

            existing_aliases = existing_entity["aliases"].to_list()[0].split(";")

            new_aliases = entity["aliases"].split(";")
            updated_aliases = list(set(existing_aliases + new_aliases))

            if updated_aliases != existing_aliases:
                self.logger.debug(
                    "Updating entity [{}] aliases: {}".format(entity_name, new_aliases)
                )
                self.entities.loc[filt, "aliases"] = ";".join(updated_aliases)

    def add_custom_entity(self, entity):
        """Add to custom entities"""
        entity_name = entity["name"]
        if not self.custom_entity_name_exists(entity_name):
            new_entity = pandas.DataFrame([entity])
            self._extracted_custom_entities = pandas.concat(
                [self._extracted_custom_entities, new_entity], ignore_index=True
            )
        else:
            filt = (
                self._extracted_custom_entities["name"].str.lower()
                == entity_name.lower()
            )
            existing_entity = self._extracted_custom_entities.loc[filt]

            existing_aliases = existing_entity["aliases"].to_list()[0].split(";")

            new_aliases = entity["aliases"].split(";")
            updated_aliases = list(set(existing_aliases + new_aliases))

            if updated_aliases != existing_aliases:
                self.logger.debug(
                    "Updating entity [{}] aliases: {}".format(entity_name, new_aliases)
                )
                self._extracted_custom_entities.loc[filt, "aliases"] = ";".join(
                    updated_aliases
                )

    def add_relationship(self, relationship):
        """Add a new relationship"""
        relationship["target"] = relationship["target"].upper()
        relationship = pandas.DataFrame([relationship])
        self._extracted_relationships = pandas.concat(
            [self._extracted_relationships, relationship], ignore_index=True
        )

    def entity_name_exists(self, name):
        """Check if entity name already exists"""
        filt = self.entities["name"].str.lower() == name.lower()
        entity = self.entities.loc[filt]
        if len(entity):
            self.logger.debug("Entity exists: {}".format(name))
            return True
        return False

    def custom_entity_name_exists(self, name):
        """Check if custom entity name already exists"""
        filt = self._extracted_custom_entities["name"].str.lower() == name.lower()
        entity = self._extracted_custom_entities.loc[filt]
        if len(entity):
            self.logger.debug("Custom entity exists: {}".format(name))
            return True
        return False

    def entity_type_from_name(self, name):
        """"""
        filt = self.entities["name"].str.lower() == name.lower()
        entity = self.entities.loc[filt]

        if len(entity):
            self.logger.debug("Entity exists: {}".format(name))
            return entity.iloc[0]["entity_type"]
        return None

    def prompt_manual_input(self, relationship):
        """Enter overrides for missing entities"""
        self.logger.info(
            "[{}] {}: {}".format(
                relationship["relationship_type"],
                colorize("UNKNOWN", "light red"),
                colorize(relationship["text"], "light gray"),
            )
        )
        isolated_entity = input("SELECTED ENTITY: ")
        if isolated_entity:
            entity_name = None
            entity_type = None
            registered_number = None

            registered_link = input("COMPANY URL: ")
            if registered_link:
                (
                    registered_number,
                    entity_type,
                ) = get_registration_number_from_link(registered_link)
                if "service.gov.uk" in registered_link:
                    entity_name = find_organisation_by_number(
                        self.companies_house_apikey,
                        registered_number,
                        self.logger,
                    )
                elif "opencorporates" in registered_link:
                    entity_name = reconcile_opencorporates_entity_by_id(
                        registered_link.split("opencorporates.com")[-1], self.logger
                    )

                elif "charitycommission" in registered_link:
                    entity_name = find_charity_by_number(
                        self.charities_apikey, registered_number, self.logger
                    )
            else:
                entity_name = input("NEW ENTITY: ")
                entity_type = input("NEW ENTITY TYPE: ")
                if not entity_name and not entity_type:
                    return None

            entity = self.make_entity_dict(
                entity_type=entity_type,
                name=entity_name,
                company_registration=registered_number,
                aliases=";".join(list(set([isolated_entity, entity_name]))),
            )
            return entity
        return None

    def log_relationship(self, index, relationship, debug_text=None):
        """Log the relationship with extracted info"""
        if relationship["target"] != "UNKNOWN":
            self.logger.info(
                "[{:05d}] [{}] {} [{} ({})] {}".format(
                    index,
                    colorize(str(relationship["source"]), "cyan"),
                    relationship["relationship_type"],
                    colorize(str(relationship["target"]), "yellow"),
                    colorize(
                        str(self.entity_type_from_name(relationship["target"])),
                        "yellow",
                    ),
                    colorize(str(relationship["text"]), "cyan"),
                )
            )
        else:
            text = str(debug_text) if debug_text else str(relationship["text"])
            self.logger.warning(
                "[{:05d}] [{}] {} {}".format(
                    index,
                    colorize(str(relationship["source"]), "cyan"),
                    colorize(relationship["relationship_type"], "blink"),
                    colorize(text, "light red"),
                )
            )

    def log_output(self):
        """Final log output"""
        taken = time.time() - self._time_start
        self.logger.info(
            "{}/{} ({}%) relationships solved (Time taken: {})".format(
                self.resolved_relationships,
                self.processed_relationships,
                int((self.resolved_relationships / self.processed_relationships) * 100),
                time.strftime("%Hh%Mm%Ss", time.gmtime(taken)),
            )
        )

    def backup_csv_files(self):
        """"""
        extracted_path = self.output_dir
        backup_path = os.path.join(extracted_path, "backup")

        if not os.path.exists(extracted_path):
            self.logger.debug("Making directoy: {}".format(extracted_path))
            os.makedirs(extracted_path)

        if not os.path.exists(backup_path):
            self.logger.debug("Making directoy: {}".format(backup_path))
            os.makedirs(backup_path)

        # backup existing csv files
        for _file in os.listdir(extracted_path):
            _filepath = os.path.join(extracted_path, _file)
            if _filepath.endswith(".csv"):
                shutil.move(_filepath, os.path.join(backup_path, _file))

    def save(self):
        """Dump the rows to csv"""
        # save out dataframes
        self._extracted_relationships.to_csv(
            self.RELATIONSHIPS_ENTITY_CSV_TEMPLATE.format(self.output_dir),
            index_label="id",
        )
        self._extracted_entities.to_csv(
            self.ENTITY_CSV_TEMPLATE.format(self.output_dir), index_label="id"
        )

        self.save_custom()
        self.logger.debug("Saved: {}".format(self.output_dir))

    def save_custom(self):
        """Dump the rows to csv"""
        # save out dataframes
        self._extracted_custom_entities.to_csv(
            self.CUSTOM_ENTITY_CSV_TEMPLATE.format(self.output_dir), index_label="id"
        )
        self.logger.debug("Saved: {}".format(self.output_dir))
