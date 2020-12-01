"""
Module for utils
"""
# -*- coding: utf-8 -*-

# sys libs
import re
import time
import json
import logging

# third party libs
import pandas
import requests
import tabula

# local libs
from .constants import REQUEST_WAIT_TIME, COMPANIES_HOUSE_QUERY_TEMPLATE, HEADERS, COMPANIES_HOUSE_PREFIXES, OPENCORPORATES_RECONCILE_URL


def get_logger(name, debug=False):
    """General purpose logger"""
    loglevel = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=loglevel,
        format="%(asctime)s %(name)s %(levelname)s:%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


def get_request(url, logger, user=None, headers=None):
    """General purpose url requests"""
    if not headers:
        headers = {}
    if user:
        request = requests.get(url, auth=(user, ""), headers=headers)
    else:
        request = requests.get(url, headers=headers)

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


def get_companies_house_company_name_from_number(
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

def extract_company_registration_number_from_text(text, logger):
    """Regex for companies house number"""
    text = (
        re.split("registration |registration number ", text)[-1]
        .strip()
        .replace(" ", "")
    )

    companies_house_pattern = "([{}|0-9]+)".format(
        "|".join(COMPANIES_HOUSE_PREFIXES)
    )
    match = re.search(companies_house_pattern, text)
    if match:
        company_number = match.groups()[0].zfill(8)
        logger.debug("Found companies house number: {}".format(company_number))
        return company_number
    return None

def reconcile_company_names(names, logger):
    """"""
    if isinstance(names, str):
        names = [names]

    query_data = {}
    for name in names:
        query_data[name] = {"query": name}

    url = "{}?queries={}&order=score".format(
        OPENCORPORATES_RECONCILE_URL, json.dumps(query_data)
    )
    request = get_request(url=url, logger=logger, user=None, headers=HEADERS)
    if request:
        return request.json()

    spoof = {}
    for name in names:
        spoof[name] = {"result": []}
    return spoof

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
