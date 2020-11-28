"""
Module for download related tasks
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import json
import urllib
import operator

# local libs
from .utils import get_request
from .constants import DATA_PARLIAMENT_QUERY_URL, THEYWORKFORYOU_QUERY_URL, HEADERS


class Download:
    """Downloader class. Queries for all members of the house of lords and commons and their
    register of financial interests. Serializes to json format"""

    def __init__(self, output_path, theyworkforyou_apikey, logger):
        self.output_path = output_path
        self.theyworkforyou_apikey = theyworkforyou_apikey
        self.logger = logger
        self.data = {}

        self.get_theyworkforyou_quota()

    def execute(self):
        """Execute"""
        self.get_members_of_parliament()
        self.save()

    def get_members_of_parliament(self):
        """Query for commons and lords data"""
        self.logger.info("Downloading data")

        commons = self.get_house_of_commons_members()
        lords = self.get_house_of_lords_members()

        # data.parliament api doesn't return the interests for commons members
        self._add_house_of_commons_members_interests(commons)

        commons.sort(key=operator.itemgetter("DisplayAs"))
        lords.sort(key=operator.itemgetter("DisplayAs"))

        self.data = {"lords": lords, "commons": commons}

    def get_theyworkforyou_quota(self):
        """Log the current theyworkforyou api quota"""
        self.logger.debug("Querying theyworkforyou quota")

        url = "{}/getQuota?key={}&output=js".format(
            THEYWORKFORYOU_QUERY_URL, self.theyworkforyou_apikey
        )
        request = get_request(url=url, logger=self.logger, user=None, headers=HEADERS)
        data = request.json()
        self.logger.info(
            "Theyworkforyou quota: {}/{}".format(
                data["quota"]["current"], data["quota"]["limit"]
            )
        )
        return data

    def _query_data_parlaiment(self, search_criteria, outputs):
        """"""
        url = "{}/{}/{}".format(DATA_PARLIAMENT_QUERY_URL, search_criteria, outputs)
        self.logger.info("Parliament Query: {}".format(url))
        request = get_request(url=url, logger=self.logger, user=None, headers=HEADERS)
        data = json.loads(request.content)
        return data

    def get_house_of_commons_members(self):
        """Query for house of commons members from data.parliament api"""
        self.logger.info("Downloading house of commons data")

        search_criteria = "House=Commons|IsEligible=true"

        outputs = "Interests|PreferredNames|GovernmentPosts|ParliamentaryPosts"
        data = self._query_data_parlaiment(search_criteria, outputs)

        outputs = "Addresses|BasicDetails"
        extra_data = self._query_data_parlaiment(search_criteria, outputs)

        for i in range(len(extra_data["Members"]["Member"])):
            data["Members"]["Member"][i]["Addresses"] = extra_data["Members"]["Member"][
                i
            ]["Addresses"]
            data["Members"]["Member"][i]["BasicDetails"] = extra_data["Members"][
                "Member"
            ][i]["BasicDetails"]

        return data["Members"]["Member"]

    def get_house_of_lords_members(self):
        """Query for house of lords members from data.parliament api"""
        self.logger.info("Downloading house of lords data")

        search_criteria = "House=Lords|IsEligible=true"

        outputs = "Interests|PreferredNames|GovernmentPosts|ParliamentaryPosts"
        data = self._query_data_parlaiment(search_criteria, outputs)

        outputs = "Addresses|BasicDetails"
        extra_data = self._query_data_parlaiment(search_criteria, outputs)

        for i in range(len(extra_data["Members"]["Member"])):
            data["Members"]["Member"][i]["Addresses"] = extra_data["Members"]["Member"][
                i
            ]["Addresses"]
            data["Members"]["Member"][i]["BasicDetails"] = extra_data["Members"][
                "Member"
            ][i]["BasicDetails"]

        return data["Members"]["Member"]

    def _add_house_of_commons_members_interests(self, commons):
        """The data.parliament doesn't return information on commons members
        financial interests. Using the theyworkforyou api, update the commons members data"""
        self.logger.info("Downloading house of commons financial interests data")

        def _get_house_of_commons_members():
            """"""
            query = {
                "key": self.theyworkforyou_apikey,
                "output": "js",
            }
            url = "{}/getMPs?{}".format(
                THEYWORKFORYOU_QUERY_URL, urllib.parse.urlencode(query)
            )

            self.logger.info("Theyworkforyou Commons Query: {}".format(url))
            request = get_request(
                url=url, logger=self.logger, user=None, headers=HEADERS
            )
            data = request.json()
            return data

        commons_members = _get_house_of_commons_members()
        person_ids = [member["person_id"] for member in commons_members]

        fields = "register_member_interests_html"
        ids = ",".join(person_ids)
        query = {
            "key": self.theyworkforyou_apikey,
            "id": ids,
            "fields": fields,
            "output": "js",
        }

        url = "{}/getMPsInfo?{}".format(
            THEYWORKFORYOU_QUERY_URL, urllib.parse.urlencode(query)
        )
        self.logger.info("Theyworkforyou Commons Info Query: {}".format(url))
        request = get_request(url=url, logger=self.logger, user=None, headers=HEADERS)
        data = request.json()

        for member in commons_members:
            member["register_member_interests_html"] = data[member["person_id"]]

        # sort commons by constituency
        commons.sort(key=operator.itemgetter("MemberFrom"))
        commons_members.sort(key=operator.itemgetter("constituency"))

        # add the interests to the existing mp dicts
        for index in enumerate(commons_members):
            commons[index[0]]["Interests"] = commons_members[index[0]][
                "register_member_interests_html"
            ]["register_member_interests_html"]

    def save(self, output_path=None):
        """Dump the data to json"""
        if not output_path:
            output_path = self.output_path

        if not os.path.exists(os.path.dirname(output_path)):
            self.logger.debug(
                "Making directoy: {}".format(os.path.dirname(output_path))
            )
            os.makedirs(os.path.dirname(output_path))

        with open(output_path, "w") as file:
            json.dump(self.data, file, sort_keys=True)
        self.logger.info("Saved: {}".format((output_path)))
