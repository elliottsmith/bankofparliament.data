"""
Constants
"""
# -*- coding: utf-8 -*-

# Named entityy recognition
NER_BASE_MODEL = "en_core_web_md"

# Neo4j
NEO4J_URL = "bolt://{}:{}"

# Download / query constants
REQUEST_WAIT_TIME = 300
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# uk government
DATA_PARLIAMENT_QUERY_URL = (
    "http://data.parliament.uk/membersdataplatform/services/mnis/members/query"
)
DATA_PARLIAMENT_LINK_URL = "https://members.parliament.uk/member/{}/{}"
SPADS_URL = "https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/854554/Annual_Report_on_Special_Advisers.pdf"

# charities
CHARITY_COMMISSION_WSDL = "https://apps.charitycommission.gov.uk/Showcharity/API/SearchCharitiesV1/SearchCharitiesV1.asmx?wsdl"

# theyworkforyou
THEYWORKFORYOU_QUERY_URL = "https://www.theyworkforyou.com/api"
THEYWORKFORYOU_LINK_URL = "https://www.theyworkforyou.com/mp/25916/{}/{}#register"

# opencorporates
OPENCORPORATES_RECONCILE_URL = "https://opencorporates.com/reconcile"
OPENCORPORATES_RECONCILE_FLYOUT_URL = "https://opencorporates.com/reconcile/flyout"

# companies house
COMPANIES_HOUSE_QUERY_LIMIT = 10
COMPANIES_HOUSE_QUERY_URL = "https://api.companieshouse.gov.uk/{}/{}"
COMPANIES_HOUSE_SEARCH_URL = (
    "https://api.companieshouse.gov.uk/search/{}?q={}&items_per_page={}"
)
COMPANIES_HOUSE_PREFIXES = [
    "AC",
    "ZC",
    "FC",
    "GE",
    "LP",
    "OC",
    "SE",
    "SA",
    "SZ",
    "SF",
    "GS",
    "SL",
    "SO",
    "SC",
    "ES",
    "NA",
    "NZ",
    "NF",
    "GN",
    "NL",
    "NC",
    "RO",
    "NI",
    "EN",
    "IP",
    "SP",
    "IC",
    "SI",
    "NP",
    "NV",
    "RC",
    "SR",
    "NR",
    "NO",
]

# Entity / relationships data structures
ENTITY_TEMPLATE = [
    "entity_type",
    "name",
    "company_registration",
    "address",
    "date_of_birth",
    "email",
    "twitter",
    "facebook",
    "linkedin",
    "aliases",
]
RELATIONSHIP_TEMPLATE = [
    "source",
    "relationship_type",
    "target",
    "date",
    "amount",
    "text",
    "link",
    "resolved",
    "original",
]

COMMONS_CATEGORIES = {
    "1": "employed_by",  # Employment and Earnings
    "2": "donations_from",  # Donations
    "3": "gifts_from",  # Gifts, Benefits and Hospitality
    "4": "visited",  # Overseas Visits
    "5": "gifts_from",  # Gifts, Benefits and Hospitality Non UK
    "6": "owner_of",  # Land and Property Portfolio
    "7": "shareholder_of",  # Shareholdings
    "8": "miscellaneous",  # Miscellaneous
    "9": "related_to",  # Family Employee
    "10": "related_to",  # Family Lobbyist
}

LORDS_CATEGORIES = {
    "Category 1": "director_of",  # Directorships
    "Category 2": "employed_by",  # Employment and Earnings
    "Category 3": "significant_control_of",  # Significant Control
    "Category 4": "shareholder_of",  # Shareholdings
    "Category 5": "owner_of",  # Land and Property Portfolio
    "Category 6": "sponsored_by",  # Sponsorship
    "Category 7": "visited",  # Overseas Visits
    "Category 8": "gifts_from",  # Gifts, Benefits and Hospitality
    "Category 9": "miscellaneous",  # Miscellaneous
    "Category 10": "miscellaneous",  # Miscellaneous
}

RELATIONSHIP_TYPES = list(
    set(list(COMMONS_CATEGORIES.values()) + list(LORDS_CATEGORIES.values()))
)
HUMAN_ENTITIES = [
    "person",
    "advisor",
    "politician",
]
POLLITICAL_ENTITIES = [
    "foreign_government",
    "government_body",
    "political_party",
    "political",
    "pollster",
    "think_lobby",
]
OTHER_ENTITIES = [
    "company",
    "association",
    "charity",
    "union",
    "education",
    "media",
    "miscellaneous",
    "sport",
    "property",
]
NON_HUMAN_ENTITIES = POLLITICAL_ENTITIES + OTHER_ENTITIES
ENTITY_TYPES = HUMAN_ENTITIES + POLLITICAL_ENTITIES + OTHER_ENTITIES

COLOR_CODES = {
    "bold": (1, 1),
    "underline": (0, 4),
    "bold-underline": (1, 4),
    "black": (0, 30),
    "dark gray": (1, 30),
    "light red": (0, 31),
    "red": (1, 31),
    "light green": (0, 32),
    "green": (1, 32),
    "brown": (0, 33),
    "yellow": (1, 33),
    "light blue": (0, 34),
    "blue": (1, 34),
    "light purple": (0, 35),
    "magenta": (1, 35),
    "light cyan": (0, 36),
    "cyan": (1, 36),
    "light gray": (0, 37),
    "white": (1, 37),
    "blink": (1, 5),
}
