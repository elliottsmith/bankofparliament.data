"""
Module for convert related tasks
"""
# -*- coding: utf-8 -*-

# sys libs
import os

# third party libs
import pandas
from bs4 import BeautifulSoup

# local libs
from .constants import (
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    DATA_PARLIAMENT_LINK_URL,
    THEYWORKFORYOU_LINK_URL,
    COMMONS_CATEGORIES,
    LORDS_CATEGORIES,
    SPADS_URL,
    ENTITY_TEMPLATE,
    RELATIONSHIP_TEMPLATE,
)
from .custom import ValueOverride
from .utils import read_json_file, read_pdf_table


class Convert:
    """Converts serialised json and pdf data to entity and relationship csv data"""

    def __init__(self, members_path, spads_path, output_dir, logger):
        """Initialise the converter instance"""
        self.output_dir = output_dir
        self.logger = logger

        self._members_data = read_json_file(members_path)
        self._spads_data = read_pdf_table(spads_path)

        self._entities = []
        self._people = []
        self._relationships = []

    def execute(self):
        """Execute"""
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
        data = dict.fromkeys(ENTITY_TEMPLATE)
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value
            else:
                self.logger.debug("Key not found in template: {}".format(key))

        self._entities.append(data)

    def add_relationship(self, **kwargs):
        """Add relationship data"""
        data = dict.fromkeys(RELATIONSHIP_TEMPLATE)
        for (key, value) in kwargs.items():
            if key in data:
                data[key] = value
            else:
                self.logger.debug("Key not found in template: {}".format(key))

        self._relationships.append(data)

    def add_parties(self):
        """Add all parties to entities"""
        for member in self.members:
            if member["Party"]["#text"] not in [
                entity["name"] for entity in self.entities
            ]:
                self.add_entity(
                    entity_type=ENTITY_TYPES[3], name=member["Party"]["#text"]
                )

    def convert_commons_members_interests(self):
        """Convert the register of interests to dict items ready for csv export"""

        # add the house of commons as an entity
        self.add_entity(entity_type=ENTITY_TYPES[4], name="House of Commons")

        for member in self.members_data["commons"]:
            self.logger.info(member["DisplayAs"])
            self.add_member_entity(member)

            # member to party relationship
            self.add_relationship(
                relationship_type=RELATIONSHIP_TYPES[1],
                source=member["DisplayAs"],
                target=member["Party"]["#text"],
                text="{} membership".format(member["Party"]["#text"]),
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

            # house of commons membership
            self.add_relationship(
                relationship_type=RELATIONSHIP_TYPES[1],
                source=member["DisplayAs"],
                target="House of Commons",
                text="Member of the House of Commons",
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

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
                    text = div.get_text().split(delimeter)

                    self.add_relationship(
                        relationship_type=last_category,
                        source=member["DisplayAs"],
                        target="UNKNOWN",
                        text=text,
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
                            text=text,
                            link=THEYWORKFORYOU_LINK_URL.format(
                                member["DisplayAs"].lower().replace(" ", "_"),
                                member["MemberFrom"].lower().replace(" ", "_"),
                            ),
                        )

                else:
                    self.logger.warning("Unrecognised div class: {}".format(div))

    def convert_lords_members_interests(self):
        """Convert the register of interests to dict items ready for csv export"""

        # add the house of lords as an entity
        self.add_entity(entity_type=ENTITY_TYPES[4], name="House of Lords")

        for member in self.members_data["lords"]:
            self.logger.info(member["DisplayAs"])
            self.add_member_entity(member)

            # member to party relationship
            self.add_relationship(
                relationship_type=RELATIONSHIP_TYPES[1],
                source=member["DisplayAs"],
                target=member["Party"]["#text"],
                text="{} membership".format(member["Party"]["#text"]),
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

            # house of lords membership
            self.add_relationship(
                relationship_type=RELATIONSHIP_TYPES[1],
                source=member["DisplayAs"],
                target="House of Lords",
                text="Member of the House of Lords",
                link=DATA_PARLIAMENT_LINK_URL.format(member["@Member_Id"], "contact"),
            )

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
                            text=[entry["RegisteredInterest"]],
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
                    self.add_entity(
                        entity_type=ENTITY_TYPES[2], name=name, aliases=name
                    )
                    self.add_relationship(
                        relationship_type=RELATIONSHIP_TYPES[2],
                        source=name,
                        target=self.get_spad_employer(last_appointer),
                        text=[str(salary), last_appointer],
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
        custom_value = ValueOverride(
            "map_values.csv", laying_minister_name, self.logger
        )
        if custom_value.converted:
            self.logger.debug(
                "Found laying minister (override): {}".format(custom_value.value)
            )
            laying_minister_name = custom_value.value

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

            elif name and laying_minister_name in name:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

            elif hansard_name and laying_minister_name in hansard_name:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

            elif laying_name and laying_minister_name in laying_name:
                self.logger.debug("Found laying minister: {}".format(member))
                return member

            else:
                self.logger.warning(
                    "Could not find laying minister: {}".format(laying_minister_name)
                )
        return None

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
            entity_type=ENTITY_TYPES[1],
            name=member["DisplayAs"],
            address=address_line,
            gender=gender,
            email=email,
            twitter=twitter,
            facebook=facebook,
            aliases=";".join(aliases),
            date_of_birth=date_of_birth,
        )

    def save(self, output_dir=None):
        """Dump the entities and relationships to csv"""
        if not output_dir:
            output_dir = self.output_dir

        if not os.path.exists(output_dir):
            self.logger.debug("Making directoy: {}".format(output_dir))
            os.makedirs(output_dir)

        relationships_csv = os.path.join(output_dir, "relationships.csv")
        relationships_dataframe = pandas.DataFrame(self.relationships)
        relationships_dataframe.to_csv(relationships_csv, index=False)

        entities_csv = os.path.join(output_dir, "entities.csv")
        entities_dataframe = pandas.DataFrame(self.entities)
        entities_dataframe.to_csv(entities_csv, index=False)

        self.logger.info("Saved: {}".format((output_dir)))
