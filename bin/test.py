#!/usr/bin/env python
"""
Script to convert raw json data to csv
"""
# -*- coding: utf-8 -*-

# sys libs
import os
import requests

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
CHARITIES_COMMISION_APIKEY = '241e3fbb-7d72-4e0e-b'
PARAMS = {
    "APIKey" : CHARITIES_COMMISION_APIKEY,
    "strSearch" : "rowntree"
}
URL = "https://beta.charitycommission.gov.uk/api/GetCharitiesByName"
request = requests.get(URL, headers=HEADERS, params=PARAMS)

print(request)