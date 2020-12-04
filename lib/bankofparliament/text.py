"""
Text cleanup
"""
# -*- coding: utf-8 -*-

# sys libs
import re
import ast

# local libs
from .patterns import IN_PARENTHESIS, POSITIONS


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


def strip_category_text(text):
    """
    Remove occurances of:
    Examples:
         '(see category 1)'
         '(see category 4(a))'
    """
    patterns = [r"\(see category [0-9]+\)", r"\(see category [0-9]+\([a-z]\)\)"]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            grps = match.group()
            text = text.replace(grps, "")
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
