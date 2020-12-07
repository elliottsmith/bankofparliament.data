"""
Module for extracting entities from relationship text
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import re
import time
import pprint

# third party
import pandas
import spacy

# local libs
from .utils import (
    read_csv_as_dataframe,
    colorize,
    find_person_by_name,
    find_organisation_by_name,
    find_organisation_by_number,
)
from .constants import (
    ENTITY_TEMPLATE,
    NER_BASE_MODEL,
    MEMBERS_CLUBS,
)
from .custom import SwapValue
from .text import (
    clean_up_significant_control,
    clean_up_directorship,
    clean_up_shareholder,
    eval_string_as_list,
    extract_company_registration_number_from_text,
)
from .relationships import get_relationship


class NamedEntityExtract:
    """Class to extract entities from raw data"""

    START = 0
    END = -1

    def __init__(
        self,
        entities,
        relationships,
        custom_entities,
        custom_relationships,
        companies_house_apikey,
        opencorporates_apikey,
        logger,
        ner_model=None,
    ):
        """Read all passed in data files"""
        self.companies_house_apikey = companies_house_apikey
        self.opencorporates_apikey = opencorporates_apikey
        self.logger = logger

        self.swap_value = SwapValue(self.logger)

        _entities = read_csv_as_dataframe(entities)
        _relationships = read_csv_as_dataframe(relationships)
        _custom_entities = read_csv_as_dataframe(custom_entities)
        _custom_relationships = read_csv_as_dataframe(custom_relationships)

        entity_data_frames = [_entities]
        if len(_custom_entities):
            entity_data_frames.append(_custom_entities)

        self._all_entities = pandas.concat(entity_data_frames, ignore_index=True)

        relationships_data_frames = [_relationships]
        if len(_custom_relationships):
            relationships_data_frames.append(_custom_relationships)

        self._all_relationships = pandas.concat(
            relationships_data_frames, ignore_index=True
        )[self.START : self.END]

        model = ner_model if ner_model else NER_BASE_MODEL
        self.logger.info("Loading NER model: {}".format(model))
        self.nlp = spacy.load(model)
        self.output_dir = os.path.dirname(entities)

    def execute(self):
        """Execute"""
        time_start = time.time()
        self.extract_entities_from_relationships()
        # self.save()
        taken = time.time() - time_start

        filt = self.relationships["target"] != "UNKNOWN"
        found = self.relationships.loc[filt]
        self.logger.info(
            "{}/{} ({}%) relationships solved (Time taken: {})".format(
                len(found),
                len(self.relationships),
                int((len(found) / len(self.relationships)) * 100),
                time.strftime("%Hh%Mm%Ss", time.gmtime(taken)),
            )
        )

    @property
    def entities(self):
        return self._all_entities

    @property
    def relationships(self):
        return self._all_relationships

    def extract_entities_from_relationships(self):
        """Extract entities from the relationships"""

        for (index, relationship) in self.relationships.iterrows():
            relationship_type = relationship["relationship_type"]
            self.log_relationship(index, relationship)

            if (
                relationship["source"] is not "UNKNOWN"
                and relationship["target"] is not "UNKNOWN"
                and self.entity_name_exists(relationship["source"])
                and self.entity_name_exists(relationship["target"])
            ):
                # self.logger.info("Source: {} and target: {} already resolved".format(relationship["source"], relationship["target"]))
                continue

            # rel = get_relationship(index, relationship, self.entities)
            # print(rel)
            # rel.evaluate()


            if relationship_type == "member_of":
                pass
                self._process_membership(index, relationship, relationship["text"])

            elif relationship_type == "significant_control_of":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                text = clean_up_significant_control(text)
                text = self.swap_value.swap(text)
                self._process_organisation(index, relationship, text)

            elif relationship_type == "director_of":
                pass
                # TODO more clean up of entry
                text = eval_string_as_list(relationship["text"])[0]
                text = clean_up_directorship(text)
                text = self.swap_value.swap(text)
                self._process_organisation(index, relationship, text)

            elif relationship_type == "related_to":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                text = self.swap_value.swap(text)
                self._process_person(index, relationship, text)

            elif relationship_type == "owner_of":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                text = self.swap_value.swap(text)
                self._process_property(index, relationship, text)

            elif relationship_type == "sponsored_by":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                text = self.swap_value.swap(text)

                result = self.nlp(text)
                people = [X.text for X in result.ents if X.label_ in ["PERSON"]]
                self._process_people(index, relationship, people)

                organisations = [
                    X.text for X in result.ents if X.label_ in ["NORP", "ORG"]
                ]
                self._process_organisations(index, relationship, organisations)

            elif relationship_type == "shareholder_of":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                text = clean_up_shareholder(text)
                text = self.swap_value.swap(text)
                self._process_organisation(index, relationship, text)

            elif relationship_type in ["donations_from", "gifts_from"]:
                pass
                texts = eval_string_as_list(relationship["text"])
                self._process_donations(index, relationship, texts)

            elif relationship_type == "visited":
                pass
                texts = eval_string_as_list(relationship["text"])
                self._process_visit(index, relationship, texts)

            elif relationship_type == "employed_by":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                self._process_ambiguous(index, relationship, text)

            elif relationship_type == "miscellaneous":
                pass
                text = eval_string_as_list(relationship["text"])[0]
                self._process_ambiguous(index, relationship, text)

            else:
                self.logger.warning(
                    "Missing relationshtip type: {}".format(relationship_type)
                )

    def _process_membership(self, index, relationship, _text):
        """
        Process membership
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target_name = _target

        filt = self.entities["name"].str.lower() == target_name.lower()
        entity = self.entities.loc[filt]
        target_type = entity.iloc[0, 0]

        self.finalise_entity(index, relationship, target_type, target_name, _text)

    def _process_association(self, index, relationship, _text):
        return self._process_non_registered_entity(
            index, relationship, _text, "association"
        )

    def _process_trade_union(self, index, relationship, _text):
        return self._process_non_registered_entity(
            index, relationship, _text, "trade_union"
        )

    def _process_ambiguous(self, index, relationship, _text):
        """
        Process ambiguous
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(colorize(_text, "cyan"), _type, _target))

        target_type = "ambiguous"
        ambiguous_name = None

        for club in MEMBERS_CLUBS:

            clean_club = re.sub("[^a-zA-Z ]+", "", _text.lower())

            # print(club.lower(), _text.lower())
            if club.lower() in clean_club:
                ambiguous_name = club.title()
                # print("FOUND CLUB: {}".format(ambiguous_name))
                return self._process_association(index, relationship, ambiguous_name)

        result = self.nlp(_text)
        organisations = [X.text for X in result.ents if X.label_ in ["NORP", "ORG"]]
        people = [X.text for X in result.ents if X.label_ in ["PERSON"]]

        for person in list(set(people)):
            person = person.title()
            ambiguous_name = person
            print("PERSON TODO: {}".format(person))
            # self._process_person(index, relationship, ambiguous_name, "person")

        for org in list(set(organisations)):
            # TODO do proper APPG regex
            org = org.title()

            if org.startswith("The "):
                ambiguous_name = org.title()
                self._process_non_registered_entity(index, relationship, ambiguous_name, target_type)

            else:
                print("ORG TODO: {}".format(org))

        if not ambiguous_name:
            relationship["target"] = (
                ambiguous_name if ambiguous_name else "UNKNOWN"
            )
            relationship["date"] = self.extract_date_from_text(_text)
            relationship["amount"] = self.extract_amount_from_text(_text)
            self.finalise_entity(
                index,
                relationship,
                target_type,
                ambiguous_name,
                _text,
            )

    def _process_non_registered_entity(self, index, relationship, _text, target_type):
        """
        Process non registered entity
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        non_registered_entity_name = None

        # TODO
        # non_registered_entity_name = find_entity_in_custom_data()

        # passthrough
        non_registered_entity_name = _text.replace(" & ", " and ")

        for starter in ["The "]:
            if non_registered_entity_name.startswith(starter):
                non_registered_entity_name = non_registered_entity_name[4:]

        non_registered_entity_name = non_registered_entity_name.strip()

        relationship["target"] = (
            non_registered_entity_name if non_registered_entity_name else "UNKNOWN"
        )
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = self.extract_amount_from_text(_text)
        self.finalise_entity(
            index,
            relationship,
            target_type,
            non_registered_entity_name,
            _text,
        )

    def _process_charity(self, index, relationship, _text):
        """
        Process charity
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target_type = "charity"
        charity_name = None
        charity_registration = None

        # TODO
        # charity_name = find_charity_by_name(_text, self.companies_house_apikey, self.logger)

        relationship["target"] = charity_name if charity_name else "UNKNOWN"
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = self.extract_amount_from_text(_text)
        self.finalise_entity(
            index,
            relationship,
            target_type,
            charity_name,
            _text,
            charity_registration,
        )

    def _process_organisation(self, index, relationship, _text, target_type="company"):
        """
        Process organisation
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        organisation_name = None
        organisation_registration = None

        (organisation_name, organisation_registration) = find_organisation_by_name(
            _text, self.companies_house_apikey, self.logger
        )

        relationship["target"] = organisation_name if organisation_name else "UNKNOWN"
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = self.extract_amount_from_text(_text)

        self.finalise_entity(
            index,
            relationship,
            target_type,
            organisation_name,
            _text,
            organisation_registration,
        )

    def _process_person(self, index, relationship, _text):
        """
        Process person
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target_name = None
        target_type = "person"

        result = self.nlp(_text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["PERSON"]:
                target_name = entity[0].title()
                break
        else:
            target_name = _text.title()

        relationship["target"] = target_name if target_name else "UNKNOWN"
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = self.extract_amount_from_text(_text)
        self.finalise_entity(index, relationship, target_type, target_name, _text)

    def _process_property(self, index, relationship, _text):
        """
        Process property
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug("{}: {} ({})".format(_text, _type, _target))

        target_name = "Property"
        target_type = "property"

        amount = 0
        if "(i)" in _text:  # indicates wealth
            amount = 0
        if "(ii)" in _text:  # indicates income from property
            amount = 10000

        relationship["target"] = target_name
        relationship["date"] = self.extract_date_from_text(_text)
        relationship["amount"] = amount
        self.finalise_entity(index, relationship, target_type, target_name, _text)

    def _process_donations(self, index, relationship, _texts):
        """
        Process donations
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug(
            "{}: {} ({})".format(_texts, colorize(_type, "magenta"), _target)
        )

        _data = self.find_key_value_pairs_from_text(_texts)

        if (
            "individual" in _data["status"].lower()
            or "private" in _data["status"].lower()
        ):
            # PERSON
            self._process_person(index, relationship, _data["name"])

        elif "charity" in _data["status"].lower():
            # CHARITY
            self._process_charity(index, relationship, _data["name"])

        elif "trade union" in _data["status"].lower():
            # TRADE UNION
            self._process_trade_union(index, relationship, _data["name"])

        elif (
            "society" in _data["status"].lower()
            or "association" in _data["status"].lower()
        ):
            # NON REGISTERED ORGANISATION
            self._process_association(index, relationship, _data["name"])

        elif "trust" in _data["status"].lower() or "other" in _data["status"].lower():
            # NON REGISTERED ORGANISATION
            self._process_non_registered_entity(
                index, relationship, _data["name"], target_type="non_registered"
            )

        elif (
            "company" in _data["status"].lower()
            or "limited liability" in _data["status"].lower()
        ):
            # COMPANY
            target_name = None
            company_registration_number = extract_company_registration_number_from_text(
                _data["status"], self.logger
            )
            if company_registration_number:
                # query companies house for company
                target_name = find_organisation_by_number(
                    self.companies_house_apikey,
                    company_registration_number,
                    self.logger,
                )

            if target_name:
                self._process_organisation(index, relationship, target_name)
            else:
                self._process_organisation(index, relationship, _data["name"])

        else:
            self._process_ambiguous(index, relationship, _texts[0])

    def _process_visit(self, index, relationship, _texts):
        """
        Process gifts
        """
        _target = relationship["target"]
        _type = relationship["relationship_type"]
        self.logger.debug(
            "{}: {} ({})".format(_texts, colorize(_type, "magenta"), _target)
        )

        if len(_texts) == 1:
            print("VISIT TODO: {}".format(_texts))
        else:
            _data = self.find_key_value_pairs_from_text(_texts)
            entities = []

            multi_entry_regex = r"\([0-9]+\) [a-zA-Z ]+"
            multi_entry_regex = r"\([0-9]+\) ([a-zA-Z ]+)"


            multi_match = re.findall(multi_entry_regex, _data["name"]) or []
            if multi_match:
                entities.extend(multi_match)
            else:
                entities = [_data["name"]]
            print("ENTITIES: {}".format(entities))





    ##########################################################################################
    # Genral Methods
    ##########################################################################################
    def _process_people(self, index, relationship, people):
        """Process people"""
        for text in people:
            self._process_person(index, relationship, text)

    def _process_organisations(self, index, relationship, organisations):
        """Process organisations"""
        for text in organisations:
            self._process_organisation(index, relationship, text)

    # def get_companies_house_entity(self, entity_type, link):

    #     url = 'https://api.companieshouse.gov.uk/%s/%s' % (entity_type, link)
    #     # print(url)

    #     headers = {"Accept": "application/json", "Content-Type": "application/json"}
    #     request = self.get_request(url=url, user=self.companies_house_apikey, headers=headers)
    #     if request:
    #         data = request.json()
    #         return data
    #     return []

    def finalise_entity(
        self,
        index,
        relationship,
        target_type,
        target_name,
        _text,
        company_registration=None,
    ):
        """Finalise the entity"""
        # self.log_relationship(index, relationship)
        if target_name:
            self.logger.info(
                "[{:05d}/{:05d}] {} Found: {} [Query Name: {}]".format(
                    index,
                    len(self.relationships),
                    target_type.title(),
                    colorize(target_name, "yellow"),
                    colorize(_text, "light blue"),
                )
            )
            self.add_entity(
                entity_type=target_type,
                name=target_name,
                company_registration=company_registration,
                aliases=[target_name],
            )
        else:
            self.logger.warning(
                "[{:05d}/{:05d}] {} NOT Found: {} [Query Name: {}]".format(
                    index,
                    len(self.relationships),
                    target_type.title(),
                    colorize(relationship["text"], "light red"),
                    _text,
                )
            )

    def add_entity(self, **kwargs):
        """Add entity data"""
        data = dict.fromkeys(ENTITY_TEMPLATE)
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value if value else "N/A"
            else:
                self.logger.debug("Key not found in template: {}".format(key))

        if not self._is_known_entity(data):
            new_entity = pandas.DataFrame([data])
            self._all_entities = pandas.concat(
                [self._all_entities, new_entity], ignore_index=True
            )

    def entity_name_exists(self, name):
        """"""
        filt = self.entities["name"].str.lower() == name.lower()
        entity = self.entities.loc[filt]
        if len(entity):
            self.logger.debug("Entity exists: {}".format(name))
            return True
        return False

    def _is_known_entity(self, data):
        """Is entity known already"""
        _entity_type = data["entity_type"]
        _name = data["name"]

        filt = (self.entities["name"].str.lower() == _name.lower()) & (
            self.entities["entity_type"].str.lower() == _entity_type.lower()
        )
        entity = self.entities.loc[filt]
        if len(entity):
            self.logger.debug("Entity exists: {}".format(_name))
            return True
        return False

    def extract_date_from_text(self, text):
        """Extract date from text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["DATE"]:
                return entity[0]
        return None

    def extract_amount_from_text(self, text):
        """Extract monetary amount from text"""
        result = self.nlp(text)
        entities = [(X.text, X.label_) for X in result.ents]
        for entity in entities:
            if entity[1] in ["MONEY"]:
                pounds = entity[0].split(".")[0]
                return re.sub("[^0-9]", "", pounds)
        return 0

    def find_key_value_pairs_from_text(self, _texts):
        """Find key/value info from list of texts"""
        data = dict.fromkeys(["name", "amount", "status", "address", "date"], "")

        for line in _texts:
            if ":" in line:
                splits = line.split(":")
                key = splits[0].strip()
                value = splits[-1].strip()
                if "name" in key.lower():
                    value = self.swap_value.swap(value)
                    data["name"] = value

                elif "amount" in key.lower() or "value" in key.lower():
                    data["amount"] = value

                elif "status" in key.lower():
                    data["status"] = value

                elif "address" in key.lower():
                    data["address"] = value

            if "registered" in line.lower():
                data["date"] = line

        return data

    def log_relationship(self, index, relationship, prefix="Relationship"):
        """Log the relationship"""
        source = relationship["source"]
        relationship_type = relationship["relationship_type"]
        target = relationship["target"]
        self.logger.debug(
            "[{:05d}/{:05d}] {}: {} ({}) {}".format(
                index,
                len(self.relationships),
                prefix,
                colorize(source, "light green"),
                colorize(relationship_type, "light cyan"),
                colorize(target, "light green"),
            )
        )

    def save(self):
        """Dump the rows to csv"""
        if not os.path.exists(self.output_dir):
            self.logger.debug("Making directoy: {}".format(self.output_dir))
            os.makedirs(self.output_dir)

        self.relationships.to_csv(
            os.path.join(self.output_dir, "relationships_extracted.csv"),
            index_label="id",
        )
        self.entities.to_csv(
            os.path.join(self.output_dir, "entities_extracted.csv"), index_label="id"
        )
        self.logger.info("Saved: {}".format(self.output_dir))
