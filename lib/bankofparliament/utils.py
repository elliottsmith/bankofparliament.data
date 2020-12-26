"""
Module for utils
"""
# -*- coding: utf-8 -*-

# sys libs
import re
import time
import json
import logging
import operator
import urllib.parse
import urllib.request

# third party libs
import pandas
import requests
import tabula
import scraperwiki
from bs4 import BeautifulSoup

# local libs
from .constants import (
    HEADERS,
    REQUEST_WAIT_TIME,
    TRADE_UNIONS_URL,
    COMPANIES_HOUSE_QUERY_URL,
    QUERY_LIMIT,
    COMPANIES_HOUSE_SEARCH_URL,
    OPENCORPORATES_RECONCILE_URL,
    OPENCORPORATES_RECONCILE_FLYOUT_URL,
    FINDTHATCHARITY_RECONCILE_URL,
    COLOR_CODES,
    ENTITY_TEMPLATE,
    RELATIONSHIP_TEMPLATE,
)

from .text import result_matches_query

# global requests session
session = requests.Session()


def get_logger(name, debug=False):
    """General purpose logger"""
    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=loglevel,
        format="%(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


def colorize(text, color):
    """Returns the specified text formatted with the specified color."""
    color = color.lower()
    if color in COLOR_CODES:
        return color_command(color) + text + color_command("reset")
    return text


def color_command(color):
    """Returns the term-compatible command associated with the specified color (or 'reset')."""
    color = color.lower()
    if color == "reset":
        return "\033[0m"
    if color in COLOR_CODES:
        code_modifier, code = COLOR_CODES[color]
        return "\033[%d;%dm" % (code_modifier, code)
    return ""


def get_request(url, logger, user=None, headers=None, params=None):
    """General purpose url requests"""
    if not headers:
        headers = {}
    if not params:
        params = {}
    if user:
        request = session.get(url, auth=(user, ""), headers=headers, params=params)
    else:
        request = session.get(url, headers=headers, params=params)

    # successfull request
    if request.status_code == 200:
        return request

    # too many requests
    if request.status_code == 429:
        logger.warning(
            "Too Many Requests, wait for {} seconds".format(REQUEST_WAIT_TIME)
        )
        time.sleep(REQUEST_WAIT_TIME)
        return get_request(url, logger, user, headers)

    # temporarily unavailable
    if request.status_code == 503:
        logger.warning(
            "Temporarily Unavailable, wait for {} seconds".format(REQUEST_WAIT_TIME)
        )
        time.sleep(REQUEST_WAIT_TIME)
        return get_request(url, logger, user, headers)

    return None


############################################################################
# reconcile functions
def reconcile_opencorporates_entity_by_name(
    name, logger, jurisdiction="gb", limit=QUERY_LIMIT
):
    """Reconcile a company name to an opencorporates record"""
    logger.debug("reconcile_opencorporates_entity_by_name: {}".format(name))
    query = {"q0": {"query": name, "limit": limit}}
    _query = json.dumps(query)
    if jurisdiction:
        params = {"queries": [_query], "jurisdiction_code": jurisdiction}
    else:
        params = {"queries": [_query]}

    request = get_request(
        OPENCORPORATES_RECONCILE_URL, logger, user=None, headers=HEADERS, params=params
    )
    if request:
        data = request.json()
        if "q0" in data:
            return data["q0"]
    return {"result": []}


def reconcile_findthatcharity_entity_by_name(
    name, logger, end_point="all", limit=QUERY_LIMIT
):
    """Reconcile a name to an findthatcharity record"""
    logger.debug("reconcile_findthatcharity_entity_by_name: {}".format(name))
    query = {"q0": {"query": name, "limit": limit}}
    _query = json.dumps(query)
    params = {"queries": [_query]}

    request = get_request(
        FINDTHATCHARITY_RECONCILE_URL.format(end_point),
        logger,
        user=None,
        headers=HEADERS,
        params=params,
    )
    if request:
        data = request.json()
        if "q0" in data:
            return data["q0"]
    return {"result": []}


def reconcile_opencorporates_entity_by_id(_id, logger):
    """Reconcile a company id to an opencorporates record"""
    params = {"id": _id}
    request = get_request(
        OPENCORPORATES_RECONCILE_FLYOUT_URL, logger, user=None, params=params
    )
    if request:
        html = request.json()["html"]
        soup = BeautifulSoup(html, features="lxml")
        title = soup.find(id="oc-flyout-title")
        if title:
            return title.text.strip()
    return None


def reconcile_findthatcharity_entity_by_id(_id, logger, end_point="all"):
    """Reconcile a findthatcharity id to an findthatcharity record"""
    logger.debug("reconcile_findthatcharity_entity_by_id: {}".format(_id))

    url = "https://findthatcharity.uk/orgid/{}".format(_id)
    html = scraperwiki.scrape(url)
    soup = BeautifulSoup(html, features="lxml")

    _name = soup.find("h2")
    if _name:
        return _name.text.strip()
    return None


def get_government_organisations(logger):
    """Get government organisations from findthatcharity"""
    return reconcile_findthatcharity_entity_by_name(
        name="*", logger=logger, limit=989, end_point="government-organisation"
    )


def get_local_authorities(logger):
    """Get local authorities from findthatcharity"""
    return reconcile_findthatcharity_entity_by_name(
        name="*", logger=logger, limit=472, end_point="local-authority"
    )


def get_universities(logger):
    """Get universities from findthatcharity"""
    return reconcile_findthatcharity_entity_by_name(
        name="*", logger=logger, limit=172, end_point="university"
    )


############################################################################
# finder functions
def findthatcharity_by_name(name, logger, end_point="all"):
    """Find a registered charity/university/local authority etc by name"""
    ELASTIC_MIN_SCORE = 999

    findthatcharity_reconcile = reconcile_findthatcharity_entity_by_name(
        name, logger, end_point
    )
    if findthatcharity_reconcile:
        results = findthatcharity_reconcile["result"]

        for result in sorted(results, key=operator.itemgetter("score"), reverse=True):
            logger.debug("CHARITY: {} {}".format(result["name"], result["score"]))

            if result["score"] > ELASTIC_MIN_SCORE:
                _name = result["name"].split("({})".format(result["id"]))[0].strip()

                organisation_registration = result["id"]
                _entity_type = result["type"][0]["id"]

                entity_type = _entity_type

                for i in ["charity", "charitable"]:
                    if i in _entity_type:
                        entity_type = "charity"

                for i in ["company", "nonprofit"]:
                    if i in _entity_type:
                        entity_type = "company"

                for i in ["education", "school", "academy", "college"]:
                    if i in _entity_type:
                        entity_type = "education"

                for i in ["sports-club"]:
                    if i in _entity_type:
                        entity_type = "sport"

                for i in ["building-society", "facility", "other", "archive", "social-housing"]:
                    if i in _entity_type:
                        entity_type = "misc"

                for i in ["health-society"]:
                    if i in _entity_type:
                        entity_type = "health"

                matched_corporate = result_matches_query(result["name"], name, logger)
                if matched_corporate:
                    return (matched_corporate, organisation_registration, entity_type)

    return (None, None, None)


def findcorporate_by_name(name, logger, jurisdiction="gb"):
    """Find a registered corporate by name"""
    ELASTIC_MIN_SCORE = 9

    entity_type = "company"
    opencorporates_reconcile = reconcile_opencorporates_entity_by_name(name, logger, jurisdiction=jurisdiction)
    if opencorporates_reconcile:
        results = opencorporates_reconcile["result"]

        for result in sorted(results, key=operator.itemgetter("score"), reverse=True):
            logger.debug("CORPORATE: {} {}".format(result["name"], result["score"]))

            if result["score"] > ELASTIC_MIN_SCORE:

                organisation_registration = result["id"].split("/")[-1]

                matched_corporate = result_matches_query(result["name"], name, logger)
                if matched_corporate:
                    return (matched_corporate, organisation_registration, entity_type)

    return (None, None, None)


def find_organisation_by_name(name, companies_house_apikey, logger):
    """Find a registered organisation by name"""
    (
        organisation_name,
        organisation_registration,
        entity_type,
    ) = findthatcharity_by_name(name, logger)
    if any((organisation_name, organisation_registration, entity_type)):
        return (organisation_name, organisation_registration, entity_type)

    (organisation_name, organisation_registration, entity_type) = findcorporate_by_name(
        name, logger, jurisdiction=None
    )
    if any((organisation_name, organisation_registration, entity_type)):
        return (organisation_name, organisation_registration, entity_type)

    return (None, None, None)


def find_organisation_by_number(companies_house_apikey, entity_number, logger):
    """Query companies house for company name"""
    url = COMPANIES_HOUSE_QUERY_URL.format("company", entity_number)
    logger.debug("Companies House Query: {}".format(url))
    request = get_request(
        url=url, logger=logger, user=companies_house_apikey, headers=HEADERS
    )
    if request:
        data = request.json()
        return data["company_name"]
    return None


############################################################################
# search functions
def search_companies_house(
    query,
    companies_house_apikey,
    logger,
    query_type="",
    limit=QUERY_LIMIT,
):
    """Search companies with text"""

    query = query.lower().strip()
    url = COMPANIES_HOUSE_SEARCH_URL.format(
        query_type, urllib.parse.quote(query), str(limit)
    )
    request = get_request(
        url=url,
        logger=logger,
        user=companies_house_apikey,
        headers=HEADERS,
    )

    if not request:
        return (None, None, None)

    data = request.json()
    for item in data["items"]:

        _name = item["title"]
        _id = item["links"]["self"].split("/")[-1]
        _snippet = item["snippet"] if "snippet" in i else None

        logger.debug(
            "COMPANIES HOUSE: {}, {} [{}]".format(_name, _id, _snippet)
        )

        matched_corporate = result_matches_query(_name, query, logger)
        if matched_corporate:
            return (matched_corporate.upper(), _id, "company")

        if _snippet:
            snippet_matched = result_matches_query(_snippet, query, logger)
            if snippet_matched:
                return (snippet_matched.upper(), _id, "company")

    return (None, None, None)


def get_list_of_trade_unions():
    """Get a list of trade unions"""
    html = scraperwiki.scrape(TRADE_UNIONS_URL)
    soup = BeautifulSoup(html, features="lxml")
    trade_unions = []
    tables = soup.find_all("table")
    for section in range(4):
        links = tables[section].find_all("a", class_="govuk-link", rel="external")
        for union in links:
            trade_unions.append(union.text)
    return trade_unions


def read_json_file(path):
    """Read json input file"""
    if path:
        with open(path, "r") as file:
            return json.load(file)
    return None


def read_pdf_table(path):
    """Read pdf input file tables"""
    if path:
        dataframe_list = tabula.read_pdf(path, pages="all", multiple_tables=True)
        return dataframe_list[1:]  # we don't need the first table
    return None


def read_csv_as_dataframe(path, null_replace="N/A", index_col="id"):
    """Read csv input file"""
    if path:
        dataframe = pandas.read_csv(path, index_col=index_col)
        return dataframe.where(pandas.notnull(dataframe), null_replace)
    return []


def make_entity_dict(**kwargs):
    """Make entity data"""
    if not "aliases" in kwargs:
        kwargs["aliases"] = [kwargs["name"]]

    # convert from list to semi-colon separated string
    # and add further aliases, replacing ampersand with 'and'
    # and vice versa
    _aliases = []
    for _alias in kwargs["aliases"]:
        _aliases.append(_alias)

        if " and " in _alias:
            _aliases.append(_alias.replace(" and ", " & "))
        elif " & " in _alias:
            _aliases.append(_alias.replace(" & ", " and "))

    alias_string = ";".join(list(set(i.lower() for i in _aliases)))
    kwargs["aliases"] = alias_string

    kwargs["name"] = kwargs["name"].upper()

    data = dict.fromkeys(ENTITY_TEMPLATE, "N/A")
    for (key, value) in kwargs.items():
        if key in data:
            data[key] = value if value else "N/A"
    return data


def make_relationship_dict(**kwargs):
    """Make relationship data"""
    data = dict.fromkeys(RELATIONSHIP_TEMPLATE, "N/A")
    for (key, value) in kwargs.items():
        if key in data:
            data[key] = value if value else "N/A"
    return data
