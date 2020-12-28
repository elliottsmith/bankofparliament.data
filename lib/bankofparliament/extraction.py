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
    make_entity_dict,
    make_relationship_dict,
    reconcile_opencorporates_entity_by_id,
    reconcile_findthatcharity_entity_by_id,
)
from .constants import NER_BASE_MODEL
from .relationships.base import get_relationship_solver


class NamedEntityExtract:
    """Class to extract entities from raw data"""

    ENTITY_CSV_TEMPLATE = "{}/entities.csv"
    RELATIONSHIPS_ENTITY_CSV_TEMPLATE = "{}/relationships.csv"

    def __init__(
        self,
        entities,
        custom_entities,
        relationships,
        companies_house_apikey,
        prompt,
        from_index,
        to_index,
        logger,
    ):
        """Read all passed in data files"""
        self._time_start = time.time()
        self.companies_house_apikey = companies_house_apikey

        self.prompt = prompt
        self.logger = logger
        self.output_dir = os.path.join(os.path.dirname(entities), "extracted")

        # read in data
        _entities = read_csv_as_dataframe(entities)
        _relationships = read_csv_as_dataframe(relationships)

        if custom_entities:
            _custom_entities = read_csv_as_dataframe(custom_entities)
            self.custom_path = custom_entities
        else:
            _custom_entities = pandas.DataFrame(columns=_entities.columns)
            self.custom_path = os.path.join(self.output_dir, "custom.csv")

        # dataframes
        self._entities = pandas.concat([_entities, _custom_entities], ignore_index=True)
        self._relationships = _relationships[from_index:to_index]

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
        self.extract_entities_from_relationships()
        self.save()
        self.log_output()

    def extract_entities_from_relationships(self):
        """Extract entities from the relationships"""
        for (index, relationship) in self.relationships.iterrows():
            self.processed_relationships += 1

            if relationship.get("resolved", "N/A") != "N/A":
                self.relationship_passthrough(
                    index, relationship, debug_text=None, resolved=True
                )
                continue

            if relationship["source"] == "UNKNOWN":
                resolved_source = self.get_missing_source_entity(relationship)
                if resolved_source:
                    relationship["source"] = resolved_source

            # get the solver for the relationship type
            solver = get_relationship_solver(
                index=index,
                relationship=relationship,
                entities=self._extracted_entities,
                nlp=self.nlp,
                companies_house_apikey=self.companies_house_apikey,
                prompt=self.prompt,
                logger=self.logger,
                parent=self,
            )

            # solve for entites, add any new ones found
            # for every entity, create a relationship from source
            if solver:
                solver.solve()

                # check to see if we have extracted entities, if we don't
                # have any, prompt for override if specified
                if not len(
                    solver.extracted_entities + solver.extracted_custom_entities
                ):
                    if self.prompt:
                        manual_entity = self.prompt_manual_input(relationship, str(solver.text))
                        if manual_entity:
                            solver.extracted_custom_entities.append(manual_entity)
                        else:
                            self.relationship_passthrough(
                                index,
                                relationship,
                                debug_text=solver.text,
                                resolved=False,
                            )
                            continue
                    else:
                        self.relationship_passthrough(
                            index, relationship, debug_text=solver.text, resolved=False
                        )
                        continue

                self.resolved_relationships += 1
                # add all the entities found and a relationship
                for entity in (
                    solver.extracted_entities + solver.extracted_custom_entities
                ):
                    self.add_entity(entity)
                    relationship = make_relationship_dict(
                        relationship_type=relationship["relationship_type"],
                        source=relationship["source"],
                        target=entity["name"],
                        date=solver.date,
                        amount=solver.amount,
                        text=relationship["text"],
                        link=relationship["link"],
                        resolved=True,
                    )
                    self.add_relationship(relationship)
                    self.log_relationship(index, relationship)

                # also save out custom entities separately
                for entity in solver.extracted_custom_entities:
                    self.add_custom_entity(entity)
                    self.save_custom()

            else:
                self.relationship_passthrough(
                    index, relationship, debug_text=None, resolved=False
                )

    def relationship_passthrough(
        self, index, relationship, debug_text=None, resolved=False
    ):
        """Passthrough for already solved relationships"""

        relationship = make_relationship_dict(
            relationship_type=relationship["relationship_type"],
            source=relationship["source"],
            target=relationship["target"],
            date=relationship["date"],
            amount=relationship["amount"],
            text=relationship["text"],
            link=relationship["link"],
            resolved=resolved,
        )
        self.add_relationship(relationship)
        self.log_relationship(index, relationship, debug_text, resolved)

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

    def add_entity(self, entity):
        """Add entity data"""
        entity_name = entity["name"]

        if not self.get_entity_name_exists(entity_name):
            new_entity = pandas.DataFrame([entity])
            self._extracted_entities = pandas.concat(
                [self._extracted_entities, new_entity], ignore_index=True
            )
        else:
            filt = self._extracted_entities["name"].str.lower() == entity_name.lower()
            existing_entity = self._extracted_entities.loc[filt]

            existing_aliases = existing_entity["aliases"].to_list()[0].split(";")

            new_aliases = entity["aliases"].split(";")
            updated_aliases = list(set(existing_aliases + new_aliases))

            if updated_aliases != existing_aliases:
                self.logger.debug(
                    "Updating entity [{}] aliases: {}".format(entity_name, new_aliases)
                )
                self._extracted_entities.loc[filt, "aliases"] = ";".join(
                    updated_aliases
                )

    def add_custom_entity(self, entity):
        """Add to custom entities"""
        entity_name = entity["name"]
        if not self.get_custom_get_entity_name_exists(entity_name):
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
                    "Updating custom entity [{}] aliases: {}".format(
                        entity_name, new_aliases
                    )
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

    def get_entity_name_exists(self, name):
        """Check if entity name already exists"""
        filt = self._extracted_entities["name"].str.lower() == name.lower()
        entity = self._extracted_entities.loc[filt]
        if len(entity):
            return True
        return False

    def get_custom_get_entity_name_exists(self, name):
        """Check if custom entity name already exists"""
        filt = self._extracted_custom_entities["name"].str.lower() == name.lower()
        entity = self._extracted_custom_entities.loc[filt]
        if len(entity):
            return True
        return False

    def get_entity_type_from_name(self, name):
        """Get the entity type from the name"""
        filt = self._extracted_entities["name"].str.lower() == name.lower()
        entity = self._extracted_entities.loc[filt]

        if len(entity):
            return entity.iloc[0]["entity_type"]
        return None

    def prompt_manual_input(self, relationship, text):
        """Enter overrides for missing entities"""
        self.logger.info(
            "[{}] {}: RAW: {} | CLEAN: {}".format(
                relationship["relationship_type"],
                colorize("PROMPT", "light red"),
                colorize(relationship["text"], "light gray"),
                colorize(text, "light gray"),
            )
        )
        isolated_entity = input("SELECTED ENTITY: ")
        if isolated_entity:
            entity_name = None
            entity_type = None
            opencorporates_registration = None
            findthatcharity_registration = None

            registered_link = input("LINK: ")
            if registered_link:

                _guess_type = None

                if "service.gov.uk" in registered_link:
                    opencorporates_registration = registered_link.split("/")[-1]
                    entity_name = reconcile_opencorporates_entity_by_id(
                        opencorporates_registration,
                        self.logger,
                    )
                    _guess_type = "company"

                elif "opencorporates" in registered_link:
                    opencorporates_registration = registered_link.split("/")[-1]
                    entity_name = reconcile_opencorporates_entity_by_id(
                        registered_link.split("opencorporates.com")[-1], self.logger
                    )
                    _guess_type = "company"

                elif "findthatcharity.uk" in registered_link:

                    findthatcharity_registration = registered_link.split("/")[-1]
                    entity_name = reconcile_findthatcharity_entity_by_id(
                        findthatcharity_registration, self.logger
                    )
                    _guess_type = "charity"

                _entity_type = input("NEW ENTITY TYPE ({}): ".format(_guess_type))
                if _entity_type == "y":
                    entity_type = _guess_type
                else:
                    entity_type = _entity_type

            else:
                entity_name = input("NEW ENTITY: ")
                entity_type = input("NEW ENTITY TYPE: ")

            if not entity_name and not entity_type:
                return None

            entity = make_entity_dict(
                entity_type=entity_type,
                name=entity_name,
                opencorporates_registration=opencorporates_registration,
                findthatcharity_registration=findthatcharity_registration,
                aliases=list(set([isolated_entity, entity_name])),
            )
            return entity
        return None

    def log_relationship(self, index, relationship, debug_text=None, resolved=False):
        """Log the relationship with extracted info"""
        exclude_from_logging = ["member_of", "related_to", "owner_of"]
        exclude_from_logging = []
        if relationship["relationship_type"] not in exclude_from_logging:

            if relationship["target"] != "UNKNOWN":
                target_entity_type = self.get_entity_type_from_name(
                    relationship["target"]
                )

                color_1 = "light cyan" if resolved else "cyan"
                color_2 = "grey" if resolved else "yellow"

                self.logger.info(
                    "[{:05d}] [{}] {} [{} ({})] {}".format(
                        index,
                        colorize(str(relationship["source"]), color_1),
                        relationship["relationship_type"],
                        colorize(str(relationship["target"]), color_2),
                        colorize(str(target_entity_type), color_2),
                        colorize(str(relationship["text"]), color_1),
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
                self.logger.warning(
                    "[{:05d}] {}".format(
                        index,
                        colorize(relationship["text"], "light red"),
                    )
                )

    def log_output(self):
        """Final log output"""
        taken = time.time() - self._time_start
        self.logger.info(
            "{}/{} ({:.2f}%) relationships solved (Time taken: {})".format(
                self.resolved_relationships,
                self.processed_relationships,
                float(
                    (self.resolved_relationships / self.processed_relationships) * 100
                ),
                time.strftime("%Hh%Mm%Ss", time.gmtime(taken)),
            )
        )

    def backup_csv_files(self):
        """Backup existing csv files"""
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
        self.save_custom()

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self._extracted_relationships.to_csv(
            self.RELATIONSHIPS_ENTITY_CSV_TEMPLATE.format(self.output_dir),
            index_label="id",
        )
        self.logger.info(
            "Saved Relationships: {}".format(
                self.RELATIONSHIPS_ENTITY_CSV_TEMPLATE.format(self.output_dir)
            )
        )

        self._extracted_entities.to_csv(
            self.ENTITY_CSV_TEMPLATE.format(self.output_dir), index_label="id"
        )
        self.logger.info(
            "Saved Entities: {}".format(
                self.ENTITY_CSV_TEMPLATE.format(self.output_dir)
            )
        )

    def save_custom(self):
        """Dump the rows to csv"""
        # save out dataframes

        if not os.path.dirname(self.custom_path):
            os.makedirs(os.path.dirname(self.custom_path))

        self._extracted_custom_entities.to_csv(self.custom_path, index_label="id")
        self.logger.info("Saved Custom: {}".format(self.custom_path))
