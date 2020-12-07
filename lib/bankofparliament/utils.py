"""
Module for utils
"""
# -*- coding: utf-8 -*-

# sys libs
import re
import time
import json
import pprint
import logging
import urllib.parse

# third party libs
import pandas
import requests
import tabula

# local libs
from .constants import (
    REQUEST_WAIT_TIME,
    COMPANIES_HOUSE_QUERY_TEMPLATE,
    HEADERS,
    COMPANIES_HOUSE_PREFIXES,
    OPENCORPORATES_RECONCILE_URL,
    COLOR_CODES,
    COMPANIES_HOUSE_QUERY_LIMIT,
    COMPANIES_HOUSE_SEARCH_TEMPLATE,
)


def get_logger(name, debug=False):
    """General purpose logger"""
    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=loglevel,
        format="%(name)s %(levelname)s:%(message)s",
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
    elif color in COLOR_CODES:
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
        request = requests.get(url, auth=(user, ""), headers=headers, params=params)
    else:
        request = requests.get(url, headers=headers, params=params)

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
    """"""
    # try reconciling it first - doesn't use up opencorporates api calls
    opencorporates_reconcile = reconcile_opencorporates_entity_by_name(name, logger)
    if opencorporates_reconcile:
        results = opencorporates_reconcile["result"]
        if len(results):
            top_match = results[0]
            if top_match["score"] > 10:
                organisation_name = top_match["name"]
                organisation_registration = top_match["id"].split("/")[-1]
                return (organisation_name, organisation_registration)

    # try localling in companies house first
    companies_house_search = search_companies_house(name, companies_house_apikey, logger, query_type="companies")
    if companies_house_search:
        return companies_house_search

    # # uses up api calls
    # opencorporates_search = search_opencorporates_company_name_from_name(*args, **kwargs)
    # if opencorporates_search:
    #     return opencorporates_search

    return (None, None)

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

def search_companies_house(query, companies_house_apikey, logger, query_type="", limit=COMPANIES_HOUSE_QUERY_LIMIT):
    """"""
    query = query.lower().strip()
    url = COMPANIES_HOUSE_SEARCH_TEMPLATE.format(query_type, urllib.parse.quote(query), str(limit))
    request = get_request(
        url=url,
        logger=logger,
        user=companies_house_apikey,
        headers=HEADERS,
    )

    if not request:
        logger.warning("Companies House Not Found: {}".format(query))
        return (None, None)

    data = request.json()
    for i in data["items"]:
        title = i["title"].lower().strip()
        snippet = i["snippet"].lower().strip() if "snippet" in i else None
        # pprint.pprint(i)

        if title in query or title.replace("ltd", "limited") in query.replace("ltd", "limited") or title.replace(".", "") in query.replace(".", ""):
            result = (i["title"], i["links"]["self"])
            logger.info("Companies House Found: {}".format(result))
            return result

        if snippet and snippet in query:
            result = (i["title"], i["links"]["self"])
            logger.info("Companies House Found: {}".format(result))
            return result

    else:
        logger.warning("Companies House Not Found: {}".format(query))
        return (None, None)

def find_person_by_name(name, logger):
    # # try reconciling it first - doesn't use up opencorporates api calls
    # opencorporates_reconcile = reconcile_opencorporates_person_name_from_name(*args, **kwargs)
    # if opencorporates_reconcile:
    #     return opencorporates_reconcile

    # # try localling in gb first
    # companies_house_search = search_companies_house_person_name_from_name(*args, **kwargs)
    # if companies_house_search:
    #     return companies_house_search

    # # uses up api calls
    # opencorporates_search = search_opencorporates_person_name_from_name(*args, **kwargs)
    # if opencorporates_search:
    #     return opencorporates_search

    return None

def find_organisation_by_number(
    companies_house_apikey, entity_number, logger
):
    """Query companies house for company name"""
    url = COMPANIES_HOUSE_QUERY_TEMPLATE.format("company", entity_number)
    logger.debug("Companies House Query: {}".format(url))
    request = get_request(
        url=url, logger=logger, user=companies_house_apikey, headers=HEADERS
    )
    if request:
        data = request.json()
        return data["company_name"]
    return None


# def get_company_name_from_number(companies_house_apikey, entity_number, logger):
#     company_name = get_companies_house_company_name_from_number(companies_house_apikey, entity_number, logger)
#     return company_name

def get_person_name_from_number(number, logger):
    pass

# def get_companies_house_company_name_from_number(
#     companies_house_apikey, entity_number, logger
# ):
#     """Query companies house for company name"""
#     url = COMPANIES_HOUSE_QUERY_TEMPLATE.format("company", entity_number)
#     logger.debug("Companies House Query: {}".format(url))
#     request = get_request(
#         url=url, logger=logger, user=companies_house_apikey, headers=HEADERS
#     )
#     if request:
#         data = request.json()
#         return data["company_name"]
#     return None

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
