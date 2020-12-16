"""
Text cleanup
"""
# -*- coding: utf-8 -*-

# sys libs
import re
import ast

# local libs
from .patterns import IN_PARENTHESIS, POSITIONS
from .constants import COMPANIES_HOUSE_PREFIXES


def eval_string_as_list(string_list):
    """Eval the string to list"""
    lines = (
        [line.strip() for line in ast.literal_eval(string_list)] if string_list else []
    )
    return lines


def clean_up_significant_control(text):
    """
    The significant control entries are almost ready for reconciliation.
    We remove some stuff after the company name that appears in parentheis
    Examples:
        Prowear 1863 to 1934 Ltd (dormant company) >>> Prowear 1863 to 1934 Ltd
        Step Foundation (interest ceased 10 December 2019) >>> Step Foundation
    """
    regex_pattern = ""
    for item in IN_PARENTHESIS:
        regex_pattern += r"\(.*{}.*\)|".format(item)
    regex_pattern = "({})".format(regex_pattern[:-1])

    match = re.search(regex_pattern, text)
    if match:
        groups = match.groups()
        for grp in groups:
            text = text.replace(grp, "")

    return text.strip()


def clean_up_directorship(text):
    """
    Entries may contain position, descriptions in parenthesis or not.
    Part of the organisation name may also contain parenthesis. Tricky.
    Examples:
        Non-executive Director, De La Rue plc (currency and authentication solutions) >>> De La Rue plc
    """
    text = strip_category_text(text)

    # Remove ay positions from text, chairman, director etc
    pattern = "{}".format(",? |".join(sorted(POSITIONS, key=len, reverse=True)))
    text = re.sub(pattern, "", text)

    parenthesis_match = find_text_within_parenthesis_excluding_other_parenthesis(text)
    if parenthesis_match:
        for match in parenthesis_match:
            if not has_consecutive_capital_letters_within_parenthesis(match):
                text = text.replace(match, "")

    splitters = ["trading as ", "investee companies", ";"]
    for splitter in splitters:
        if splitter in text:
            text = text.split(splitter)[0]

    starters = ["and ", ", ", "of "]
    for starter in starters:
        if text.startswith(starter):
            text = text[len(starter) :]

    text = text.replace("  ", " ")
    return text.strip()


def clean_up_shareholder(text):
    """"""
    text = strip_category_text(text)
    text = strip_registered_text(text)

    # Remove ay positions from text, chairman, director etc
    pattern = "{}".format(",? |".join(sorted(POSITIONS, key=len, reverse=True)))
    text = re.sub(pattern, "", text)

    parenthesis_match = find_text_within_parenthesis_excluding_other_parenthesis(text)
    if parenthesis_match:
        for match in parenthesis_match:
            if not has_consecutive_capital_letters_within_parenthesis(match):
                text = text.replace(match, "")

    splitters = [
        "trading as ",
        "investee companies",
        ";",
        ":",
        ", a",
        ", marketing consultancy",
        ", financial services company",
        ", psychology assessment",
        ", tour operator",
        ", shares co-owned",
        ". UK property company",
        ", Sporting Video Company",
        ", management of",
        "family business",
        "in the EdTech space",
        "SIPP",
        "per cent ownership",
        r"% ownership",
    ]
    for splitter in splitters:
        if splitter in text:
            text = text.split(splitter)[0]

    starters = ["and ", ", ", "of ", "in "]
    for starter in starters:
        if text.startswith(starter):
            text = text[len(starter) :]

    enders = ["."]
    for ender in enders:
        if text.endswith(ender):
            text = text[: len(ender)]

    from_until_pattern = "(Until [a-zA-Z0-9 ]+,)|(From [a-zA-Z0-9 ]+,)"
    match = re.search(from_until_pattern, text)
    if match:
        grps = match.group()
        text = text.replace(grps, "")

    text = text.replace("  ", " ")
    return text.strip()


def strip_category_text(text):
    """
    Remove occurances of:
    Examples:
         '(see category 1)'
         '(see category 4(a))'
    """
    patterns = [r"\(see category [0-9]+\)", r"\(see category [0-9]+\([a-z]\)\)"]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            grps = match.groups()
            for grp in grps:
                text = text.replace(grp, "")
    return text


def strip_registered_text(text):
    """
    Remove occurances of:
    Examples:
         'Millgap Ltd; consulting, advisory and investment (Registered 05 June 2015)'
    """
    patterns = [r"(\(Registered.*\))", r"(\(Updated.*\))"]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            grps = match.groups()
            for grp in grps:
                text = text.replace(grp, "")
    return text


def strip_positions_text(text):
    """Remove a job title from text"""
    # Remove ay positions from text, chairman, director etc
    pattern = "{}".format(",? |".join(sorted(POSITIONS, key=len, reverse=True)))
    text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def strip_from_dates_text(text):
    """Remove dates from text"""
    from_until_pattern = "(until [a-zA-Z0-9 ]+,)|(from [a-zA-Z0-9 ]+,)"
    match = re.search(from_until_pattern, text, flags=re.IGNORECASE)
    if match:
        grps = match.groups()
        for grp in grps:
            if grp:
                text = text.replace(grp, "")
    return text


def strip_parenthesis_text(text):
    """Remove text within parenthesis from text"""
    parenthesis_match = find_text_within_parenthesis_excluding_other_parenthesis(text)
    if parenthesis_match:
        for match in parenthesis_match:
            if not has_consecutive_capital_letters_within_parenthesis(match):
                text = text.replace(match, "")
    return text


def has_consecutive_capital_letters_within_parenthesis(text):
    """
    There may be some text within parenthesis that we want to keep
    Examples:
        'A company (UK) Ltd' - keep this
        'A company (agriculture)' - drop this
    """
    pattern = r"(\([A-Z0-9 ]{2,}\))"
    match = re.search(pattern, text)
    if match:
        return True
    return False


def find_text_within_parenthesis_excluding_other_parenthesis(text):
    """
    Find text within parenthesis
    Examples:
        'Director, The Big Issue Cymru Limited (Wales edition of Big Issue magazine)
    """
    pattern = r"(\([^(^)]+\))"
    match = re.findall(pattern, text)
    return match


def extract_company_registration_number_from_text(text, logger):
    """
    Regex for companies house number
    """
    text = (
        re.split("registration |registration number ", text)[-1]
        .strip()
        .replace(" ", "")
    )

    companies_house_pattern = "([{}|0-9]+)".format("|".join(COMPANIES_HOUSE_PREFIXES))
    match = re.search(companies_house_pattern, text)
    if match:
        company_number = match.groups()[0].zfill(8)
        logger.debug("Found companies house number: {}".format(company_number))
        return company_number
    return None


def get_registration_number_from_link(url):
    """"""
    registration_number = None
    if "service.gov.uk" in url:
        registration_number = url.split("/")[-1]
        entity_type = "company"

    elif "charitycommission.gov.uk" in url:
        registration_number = url.split("/")[-1]
        entity_type = "charity"

    elif "opencorporates.com" in url:
        registration_number = url.split("/")[-1]
        entity_type = "company"

    return (registration_number, entity_type)


def get_property_multiplier(text):
    """Get multiplier from text"""
    property_multipliers = {
        0.33: ["third share"],
        0.5: ["half", "a share", "50%"],
        1: ["one"],
        2: ["two", "various", "flats"],
        3: ["three"],
        4: ["four"],
        5: ["five"],
        6: ["six"],
        7: ["seven"],
        8: ["eight"],
        9: ["nine"],
        10: ["ten"],
    }

    for (multiplier, values) in property_multipliers.items():
        for identifier in values:
            if "{} ".format(identifier).lower() in text.lower():
                return multiplier
    return 1
