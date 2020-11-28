"""
Module for utils
"""
# -*- coding: utf-8 -*-

# sys libs
import time
import json
import logging

# third party libs
import requests
import tabula

# local libs
from .constants import REQUEST_WAIT_TIME


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
