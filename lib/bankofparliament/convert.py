"""
Module for convert related tasks
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import re

# third party libs
import pandas
from bs4 import BeautifulSoup

# local libs
from .constants import (
    DATA_PARLIAMENT_LINK_URL,
    THEYWORKFORYOU_LINK_URL,
    COMMONS_CATEGORIES,
    LORDS_CATEGORIES,
    SPADS_URL,
)
from .custom import SwapValue
from .utils import (
    read_json_file,
    read_pdf_table,
    make_entity_dict,
    make_relationship_dict,
)


class Convert:
    """Converts serialised json and pdf data to entity and relationship csv data"""

    MINIMUM_SOUP_LENGTH = 3

    def __init__(self, members_path, spads_path, output_dir, logger):
        """Initialise the converter instance"""
        self.output_dir = output_dir
        self.logger = logger

        self._members_data = read_json_file(members_path)
        self._spads_data = read_pdf_table(spads_path)
        self.swap_value = SwapValue(self.logger)

        self._entities = []
        self._relationships = []

    def execute(self):
        """Execute"""
        self.add_constitutional_monarchy()
        self.add_parties()
        self.convert_commons_members_interests()
        self.convert_lords_members_interests()
        if self._spads_data:
            self.convert_spads()
        self.save()

    @property
    def entities(self):
        return self._entities

    @property
    def relationships(self):
        return self._relationships

    @property
    def spads_data(self):
        return self._spads_data

    @property
    def members(self):
        return self._members_data["commons"] + self._members_data["lords"]

    @property
    def members_data(self):
        return self._members_data

    def add_entity(self, **kwargs):
        """Add entity data"""
        data = make_entity_dict(**kwargs)
        self._entities.append(data)

    def add_relationship(self, **kwargs):
        """Add relationship data"""
        data = make_relationship_dict(**kwargs)
        self._relationships.append(data)

    def add_constitutional_monarchy(self):
        """Add a basic skeleton of the UK's constitutional monarchy"""

        # monarchy
        self.add_entity(
            entity_type="state_power", name="The Crown", aliases=["The Monarchy"]
        )

        # separation of powers
        state_powers = [
            "Judicary",
            "Church of England",
            "British Armed Forces",
            "Her Majesty's Government",
        ]
        for power in state_powers:
            self.add_entity(entity_type="state_power", name=power)
            self.add_relationship(
                source="The Crown",
                relationship_type="constitutional_head_of",
                target=power,
                text=["Constitutional head of {}".format(power)],
            )

        self.add_entity(
            entity_type="house_of_parliament",
            name="House of Commons",
            aliases=["The Commons"],
        )
        self.add_entity(
            entity_type="house_of_parliament",
            name="House of Lords",
            aliases=["The Lords"],
        )

    def add_parties(self):
        """Add all parties to entities"""
        for member in self.members:
            party = self.cleanup_party_affliation(member["Party"]["#text"])
            _aliases = [party]
            if len(member["Party"]["#text"].split()) > 1:
                _aliases.append(member["Party"]["#text"])
            aliases = list(set(_aliases))
            if party.upper() not in [entity["name"] for entity in self.entities]:
                self.add_entity(
                    entity_type="political_party", name=party, aliases=aliases
                )

    def convert_commons_members_interests(self):
        """Convert the register of interests to dict items ready for csv export"""

        for member in self.members_data["commons"]:
            self.logger.info(member["DisplayAs"])
            self.add_member_entity(member)

            # member to party relationship
            self.add_relationship(
                relationship_type="member_of",
                source=member["DisplayAs"],
                target=self.cleanup_party_affliation(member["Party"]["#text"]),
                text=["{} membership".format(member["Party"]["#text"])],
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

            # house of commons membership
            self.add_relationship(
                relationship_type="member_of",
                source=member["DisplayAs"],
                target="House of Commons",
                text=["Member of the House of Commons"],
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

            # government relationship
            self.add_government_relationship(member)

            # financial interests relationships
            soup = BeautifulSoup(member["Interests"], features="lxml")
            last_category = None

            for div in soup.find_all("div"):
                if "regmemcategory" in div.attrs["class"]:
                    for index in COMMONS_CATEGORIES:
                        if div.text.startswith(str(index)):
                            last_category = COMMONS_CATEGORIES[index]

                elif "regmemitem" in div.attrs["class"]:
                    delimeter = "?????"
                    for line_break in div.findAll("br"):
                        line_break.replaceWith(delimeter)
                    _texts = re.sub("\r|\n", " ", div.get_text()).split(delimeter)

                    texts = [
                        text for text in _texts if len(text) > self.MINIMUM_SOUP_LENGTH
                    ]

                    if texts:
                        self.add_relationship(
                            relationship_type=last_category,
                            source=member["DisplayAs"],
                            target="UNKNOWN",
                            text=texts,
                            link=THEYWORKFORYOU_LINK_URL.format(
                                member["DisplayAs"].lower().replace(" ", "_"),
                                member["MemberFrom"].lower().replace(" ", "_"),
                            ),
                        )

                    if last_category == "related_to":
                        # add a second relationship, from target > source - employment
                        self.add_relationship(
                            relationship_type="employed_by",
                            source="UNKNOWN",
                            target=member["DisplayAs"],
                            text=["Am employed by {}".format(member["DisplayAs"])],
                            link=THEYWORKFORYOU_LINK_URL.format(
                                member["DisplayAs"].lower().replace(" ", "_"),
                                member["MemberFrom"].lower().replace(" ", "_"),
                            ),
                        )

                else:
                    self.logger.warning("Unrecognised div class: {}".format(div))

    def convert_lords_members_interests(self):
        """Convert the register of interests to dict items ready for csv export"""

        for member in self.members_data["lords"]:
            self.logger.info(member["DisplayAs"])
            self.add_member_entity(member)

            # member to party relationship
            self.add_relationship(
                relationship_type="member_of",
                source=member["DisplayAs"],
                target=self.cleanup_party_affliation(member["Party"]["#text"]),
                text=["{} membership".format(member["Party"]["#text"])],
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

            # house of lords membership
            self.add_relationship(
                relationship_type="member_of",
                source=member["DisplayAs"],
                target="House of Lords",
                text=["Member of the House of Lords"],
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

            # government relationship
            self.add_government_relationship(member)

            # financial interests relationships
            if member["Interests"]:
                if isinstance(member["Interests"]["Category"], dict):
                    continue

                last_category = None
                interests = member["Interests"]["Category"]
                for category in interests:

                    for index in LORDS_CATEGORIES:
                        if category["@Name"].startswith(str(index)):
                            last_category = LORDS_CATEGORIES[index]

                    if isinstance(category["Interest"], dict):
                        interests = [category["Interest"]]
                    else:
                        interests = category["Interest"]

                    for entry in interests:
                        self.add_relationship(
                            relationship_type=last_category,
                            source=member["DisplayAs"],
                            target="UNKNOWN",
                            text=[re.sub("\r|\n", " ", entry["RegisteredInterest"])],
                            link=DATA_PARLIAMENT_LINK_URL.format(
                                member["@Member_Id"], "registeredinterests"
                            ),
                            date=entry["Created"],
                        )

                    if not last_category:
                        self.logger.warning(
                            "Unrecognised category: {}".format(category["@Name"])
                        )

    def convert_spads(self):
        """Convert the spad data to dict items ready for csv export"""

        last_appointer = None
        for table in self.spads_data:
            table = table.where(pandas.notnull(table), None)
            for spad in table.itertuples(name=None):
                name = None
                salary = None

                if spad[2]:
                    name = spad[2].replace("\r", " ")
                if spad[4]:
                    salary = spad[4].replace("\r", " ")

                try:
                    # the table contents is weirdly formatted in the pdf
                    # some rows use different indices
                    # if we can convert the name to an int, that's bad
                    int(name)
                    name = spad[1].replace("\r", "")
                    salary = spad[3]
                except:
                    if spad[1]:
                        last_appointer = spad[1].replace("\r", " ")

                if name and last_appointer and salary:
                    self.logger.info(name)
                    self.add_entity(entity_type="advisor", name=name, aliases=[name])

                    resolved_employer = self.get_spad_employer(last_appointer)
                    self.add_relationship(
                        relationship_type="employed_by",
                        source=name,
                        target=resolved_employer,
                        text=[
                            "I am employed by {} on a salary of {}".format(
                                resolved_employer, str(salary.split("-")[0])
                            )
                        ],
                        link=SPADS_URL,
                    )

    def get_spad_employer(self, government_position):
        """Convert a government position to a member name"""

        def _get_government_posts():
            """Find all governments posts currently active"""
            government_posts = []
            for member in self.members_data["commons"] + self.members_data["lords"]:
                if member.get("GovernmentPosts", None) or []:
                    posts = member["GovernmentPosts"]["GovernmentPost"]
                    if isinstance(posts, dict):
                        posts = [posts]

                    for post in posts:
                        if not post["EndDate"]:
                            government_posts.append((post, member["DisplayAs"]))

            return government_posts

        government_posts = _get_government_posts()
        spad_employer = self._get_member_from_laying_minister_name(
            government_position, government_posts
        )
        return spad_employer

    def _get_member_from_laying_minister_name(
        self, laying_minister_name, government_posts
    ):
        """Resolve a laying minister name to an entity"""
        # there are some names here, that don't correspond exactly to laying
        # ministers names, let's check our custom values first
        laying_minister_name = self.swap_value.swap(laying_minister_name)

        def _loop_members():
            """Members generator"""
            for member in self.members:
                yield member

        for member in _loop_members():
            if laying_minister_name == member.get("LayingMinisterName", None):
                self.logger.debug(
                    "Found laying minister: {}".format(member["DisplayAs"])
                )
                return member["DisplayAs"]

        for (post, member) in government_posts:
            name = post.get("Name", None)
            hansard_name = post.get("HansardName", None)
            laying_name = post.get("LayingMinisterName", None)

            if laying_minister_name in [name, hansard_name, laying_name]:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

            if name and laying_minister_name in name:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

            if hansard_name and laying_minister_name in hansard_name:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

            if laying_name and laying_minister_name in laying_name:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

        self.logger.warning(
            "Could not find laying minister: {}".format(laying_minister_name)
        )
        return None

    def add_government_relationship(self, member):
        """If the member has a government post, add a relationship"""
        # government relationship
        if member.get("GovernmentPosts", None) or []:
            posts = member["GovernmentPosts"]["GovernmentPost"]
            if isinstance(posts, dict):
                posts = [posts]

            for post in posts:
                if not post["EndDate"]:
                    self.add_relationship(
                        source=member["DisplayAs"],
                        relationship_type="member_of",
                        target="Her Majesty's Government",
                        text=["Member of Her Majesty's Government"],
                        link=DATA_PARLIAMENT_LINK_URL.format(
                            member["@Member_Id"], "contact"
                        ),
                    )

    def convert_donations(self):
        """Convert other political donations"""
        raise NotImplementedError

    def convert_government_contracts(self):
        """Convert government outsource contracts"""
        raise NotImplementedError

    def convert_lobbyists(self):
        """Convert lobbyists data"""
        raise NotImplementedError

    def convert_acoba(self):
        """Convert acoba data"""
        raise NotImplementedError

    def add_member_entity(self, member):
        """Add a member record to entities"""
        date_of_birth = None
        if isinstance(member["DateOfBirth"], str):
            date_of_birth = member["DateOfBirth"]

        gender = None
        if isinstance(member["Gender"], str):
            gender = member["Gender"]

        addresses = []
        if member.get("Addresses", False):
            if isinstance(member["Addresses"]["Address"], dict):
                addresses = [member["Addresses"]["Address"]]
            else:
                addresses = member["Addresses"]["Address"]

        email = None
        twitter = None
        facebook = None
        opencorporates_registration = None
        findthatcharity_registration = None
        address_line = ""
        for address in addresses:

            if address["Type"] == "Twitter":
                twitter = address["Address1"]
            elif address["Type"] == "Facebook":
                facebook = address["Address1"]
            elif address["Type"] == "Parliamentary":
                email = address.get("Email", None)
            elif address["Type"] == "Constituency":
                for (key, value) in address.items():
                    if "Address" in key and value and value != "Constituency office":
                        address_line += "{} ".format(value)
                address_line += " {}".format(address["Postcode"])

        preferred_names = []
        if member.get("PreferredNames", False):
            if isinstance(member["PreferredNames"]["PreferredName"], dict):
                preferred_names = [member["PreferredNames"]["PreferredName"]]
            else:
                preferred_names = member["PreferredNames"]["PreferredName"]

        aliases = [member["DisplayAs"], member["FullTitle"]]
        for name in preferred_names:
            aliases.append(name["DisplayAs"])
            aliases.append(name["AddressAs"])
            aliases.append(name["FullTitle"])

            if name["Forename"] and name["Surname"]:
                first_middle_last = name["Forename"]
                if name["MiddleNames"]:
                    first_middle_last += " {}".format(name["MiddleNames"])
                first_middle_last += " {}".format(name["Surname"])
                aliases.append(first_middle_last)
        aliases = list(set(aliases + [member["DisplayAs"]]))
        aliases = [i.strip().replace("  ", " ") for i in aliases if i]

        self.add_entity(
            entity_type="politician",
            name=member["DisplayAs"],
            opencorporates_registration=opencorporates_registration,
            findthatcharity_registration=findthatcharity_registration,
            address=address_line,
            gender=gender,
            email=email,
            twitter=twitter,
            facebook=facebook,
            aliases=aliases,
            date_of_birth=date_of_birth,
        )

    def cleanup_party_affliation(self, party):
        """Cleanup party affliation"""
        non_affiliated = [
            "Non-affiliated",
            "Bishops",
            "Speaker",
            "Lord Speaker",
            "Crossbench",
            "Independent",
        ]

        if "labour" in party.lower():
            party = "Labour"
        elif "conservative" in party.lower():
            party = "Conservative"
        elif "ulster unionist" in party.lower():
            party = "Ulster Unionist"
        elif "social democrat" in party.lower():
            party = "Social Democrat"

        if party not in non_affiliated and not party.lower().endswith("party"):
            party += " Party"

        return party

    def save(self, output_dir=None):
        """Dump the entities and relationships to csv"""
        if not output_dir:
            output_dir = self.output_dir

        if not os.path.exists(output_dir):
            self.logger.debug("Making directoy: {}".format(output_dir))
            os.makedirs(output_dir)

        relationships_csv = os.path.join(output_dir, "relationships.csv")
        relationships_dataframe = pandas.DataFrame(self.relationships)
        relationships_dataframe.to_csv(relationships_csv, index_label="id")

        entities_csv = os.path.join(output_dir, "entities.csv")
        entities_dataframe = pandas.DataFrame(self.entities)
        entities_dataframe.to_csv(entities_csv, index_label="id")

        self.logger.info("Saved: {}".format((output_dir)))
