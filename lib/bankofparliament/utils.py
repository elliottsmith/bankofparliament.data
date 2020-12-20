"""
Module for utils
"""
# -*- coding: utf-8 -*-

# sys libs
import time
import json
import logging
import urllib.parse
import urllib.request

# third party libs
import pandas
import requests
import tabula
from bs4 import BeautifulSoup
import zeep

# local libs
from .constants import (
    HEADERS,
    REQUEST_WAIT_TIME,
    COMPANIES_HOUSE_QUERY_URL,
    COMPANIES_HOUSE_QUERY_LIMIT,
    COMPANIES_HOUSE_SEARCH_URL,
    OPENCORPORATES_RECONCILE_URL,
    OPENCORPORATES_RECONCILE_FLYOUT_URL,
    CHARITY_COMMISSION_WSDL,
    FINDTHATCHARITY_RECONCILE_URL,
    COLOR_CODES,
    ENTITY_TEMPLATE,
    RELATIONSHIP_TEMPLATE
)

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


def find_organisation_by_name(name, companies_house_apikey, logger):
    """Find a registered organisation by name"""
    # try reconciling it first - doesn't use up api calls

    findthatcharity_reconcile = reconcile_findthatcharity_entity_by_name(name, logger)
    if findthatcharity_reconcile:
        results = findthatcharity_reconcile["result"]
        if len(results):
            top_match = results[0]
            if top_match["score"] > 1000:
                organisation_name = top_match["name"].upper()
                organisation_registration = top_match["id"].split("/")[-1]
                entity_type = top_match["type"][0]["id"]
                return (organisation_name, organisation_registration, entity_type)

    opencorporates_reconcile = reconcile_opencorporates_entity_by_name(name, logger)
    if opencorporates_reconcile:
        results = opencorporates_reconcile["result"]
        if len(results):
            top_match = results[0]
            if top_match["score"] > 10:
                organisation_name = top_match["name"].upper()
                organisation_registration = top_match["id"].split("/")[-1]
                return (organisation_name, organisation_registration, "company")

    # try locally in companies house first
    companies_house_search = search_companies_house(
        name, companies_house_apikey, logger, query_type="companies"
    )
    if companies_house_search:
        return companies_house_search

    return (None, None, None)


def reconcile_opencorporates_entity_by_name(name, logger):
    """Reconcile a company name to an opencorporates record"""
    params = {"query": name}
    request = get_request(
        OPENCORPORATES_RECONCILE_URL, logger, user=None, headers=HEADERS, params=params
    )
    if request:
        data = request.json()
        if "result" in data:
            return data
    return {"result": []}


def reconcile_opencorporates_entity_by_id(_id, logger):
    """Reconcile a company name to an opencorporates record"""
    params = {"id": _id}
    request = get_request(
        OPENCORPORATES_RECONCILE_FLYOUT_URL, logger, user=None, params=params
    )
    if request:
        html = request.json()["html"]
        soup = BeautifulSoup(html, features="lxml")
        title = soup.find(id="oc-flyout-title")
        if title:
            return title.text
    return None


def reconcile_findthatcharity_entity_by_name(name, logger, limit=5, end_point="all"):
    """Reconcile a company name to an findthatcharity record"""
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
def search_companies_house(
    query,
    companies_house_apikey,
    logger,
    query_type="",
    limit=COMPANIES_HOUSE_QUERY_LIMIT,
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
    for i in data["items"]:
        title = i["title"].lower().strip()
        snippet = i["snippet"].lower().strip() if "snippet" in i else None

        if (
            title in query
            or title.replace("ltd", "limited") in query.replace("ltd", "limited")
            or title.replace(".", "") in query.replace(".", "")
            and len(snippet) > 2
        ):
            result = (i["title"].upper(), i["links"]["self"], "company")
            return result

        if snippet and snippet in query and len(snippet) > 2:
            result = (i["title"].upper(), i["links"]["self"], "company")
            return result

    return (None, None, None)
    return (None, None)


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


def get_zeep_client(wsdl, api_key_name, api_key_value):
    """Get an SOAP zeep client"""

    class CharitiesAuthPlugin(zeep.Plugin):

        """Add an APIKey to each request."""

        def __init__(self, api_key_name, api_key_value):
            """Initialise api_key_name and api_key_value."""
            self.api_key_name = api_key_name
            self.api_key_value = api_key_value

        def egress(self, envelope, http_headers, operation, binding_options):
            """Auto add to the envelope (or replace) Charity api_key.
            :param envelope: The envelope as XML node
            :param http_headers: Dict with the HTTP headers
            :param operation: The associated Operation instance
            :param binding_options: Binding specific options for the operation
            """
            for element in operation.input.body.type.elements:
                if (
                    element[0] == self.api_key_name
                    and element[1].name == self.api_key_name
                ):
                    key_type = element[1]
                    key_type.render(envelope[0][0], self.api_key_value)
            return envelope, http_headers

    settings = zeep.Settings(strict=False, xml_huge_tree=True, raw_response=False)
    plugins = [CharitiesAuthPlugin(api_key_name, api_key_value)]
    return zeep.Client(wsdl=wsdl, settings=settings, plugins=plugins)


def find_charity_by_number(charities_apikey, registered_number, logger):
    """Find charity by number"""
    logger.debug("Query charities commission: {}".format(registered_number))
    client = get_zeep_client(CHARITY_COMMISSION_WSDL, "APIKey", charities_apikey)
    charity = client.service.GetCharityByRegisteredCharityNumber(
        registeredCharityNumber=str(registered_number)
    )
    if charity:
        return charity["CharityName"]
    return None


def find_charity_by_name(charities_apikey, name, logger):
    """Find charity by name"""
    logger.debug("Query charities commission: {}".format(name))
    client = get_zeep_client(CHARITY_COMMISSION_WSDL, "APIKey", charities_apikey)
    charity = client.service.GetCharityByName(strSearch=str(name))
    if charity:
        return charity["CharityName"]
    return None


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

    alias_string = ";".join(list(set(_aliases)))
    kwargs["aliases"] = alias_string

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
