"""
Text cleanup
"""
# -*- coding: utf-8 -*-

# sys libs
import re
import ast
import string

# local libs
from .patterns import IN_PARENTHESIS, POSITIONS, FINANCIAL_SUFFIXES
from .constants import COMPANIES_HOUSE_PREFIXES

# third party
import pyap
from cleanco import prepare_terms, basename
from nltk.corpus import stopwords
from nltk import word_tokenize

terms = prepare_terms()


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
    patterns = [r"(\(?see category [0-9]+\(?[a-z]?\)?\))"]
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

def strip_dates_text(nlp, text):
    """"""
    result = nlp(text=text)
    entities = [(X.text, X.label_) for X in result.ents]

    for entity in entities:
        if entity[1] in ["DATE", "TIME", "MONEY", "QUANTITY"]:
            _name = entity[0]
            text = text.replace(_name, " ")
    return text

def strip_parenthesis_text(text):
    """Remove text within parenthesis from text"""
    parenthesis_match = find_text_within_parenthesis_excluding_other_parenthesis(text)
    if parenthesis_match:
        for match in parenthesis_match:
            if not has_consecutive_capital_letters_within_parenthesis(match):
                text = text.replace(match, "")
    return text

def strip_share_class(nlp, text):
    """"""
    patterns = [r"(Ord[inary]?[ 0-9a-zA-Z]+Shares? ?[0-9\(.,:;%\)]+)", r"({}).+".format("|".join(FINANCIAL_SUFFIXES))]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            grps = match.groups()
            for grp in grps:
                if grp:
                    text = text.replace(grp, "")

    result = nlp(text=text)
    entities = [(X.text, X.label_) for X in result.ents]

    for entity in entities:
        if entity[1] in ["MONEY", "QUANTITY", "ORD"]:
            _name = entity[0]
            text = text.replace(_name, " ")

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
    pattern = r"(\([^(^)]+\)?)"
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

def strip_address_text(text):
    """"""
    try:
        text = eval_string_as_list(text)[0]
    except:
        text = text

    addresses = pyap.parse(text, country='GB')
    if addresses:
        for addr in addresses:
            text = text.replace(addr.full_address, " ")
    return text

def normalise_organisation_name(_name):
    """Normalise organisation name"""
    _name = strip_organisation_type(_name)
    _name = strip_punctuation(_name)
    _name = strip_stopwords(_name)
    return _name


def strip_punctuation(text):
    """Remove punctuation from text"""
    table = str.maketrans(string.punctuation + "’", " "*33)
    text = text.translate(table)
    return text.replace("  ", " ")


def strip_organisation_type(text):
    """Remove organisation types, ltd, plc, inc etc from text"""
    return basename(text, terms, prefix=False, middle=False, suffix=True)


def strip_stopwords(text):
    """Remove nltk stopwords from text"""
    _tokens = word_tokenize(text)
    _tokens = [t.lower() for t in _tokens]
    _tokens = [t for t in _tokens if t not in stopwords.words("english")]
    return " ".join(_tokens)

def strip_non_alphanumeric(text):
    """"""
    return re.sub("[\W_]", "", text)


def result_matches_query(name, query, logger, min_word_length=2):
    """Evaluate if a query matches an organisation name"""
    possibles = []

    _name = name.lower()
    _query = query.lower()

    if (
        strip_punctuation(_name) == strip_punctuation(_query)
        and len(query.split()) >= min_word_length
    ):
        logger.debug("Matched: {} ---> {}".format(query, name))
        return name.upper()

    normalised_name = normalise_organisation_name(_name)
    normalised_query = normalise_organisation_name(_query)
    logger.debug(normalised_name)
    logger.debug(normalised_query)

    if normalised_name == normalised_query:
        if len(query.split()) >= min_word_length:
            logger.debug("Matched: {} ---> {}".format(query, name))
            return name.upper()
        possibles.append(name)

    if normalised_name in normalised_query:
        if len(normalised_name.split()) > min_word_length:
            logger.debug("Matched: {} ---> {}".format(query, name))
            return name.upper()
        possibles.append(name)

    elif normalised_query in normalised_name:
        if len(normalised_query.split()) > min_word_length:
            logger.debug("Matched: {} ---> {}".format(query, name))
            return name.upper()
        possibles.append(name)

    if strip_non_alphanumeric(normalised_name) == strip_non_alphanumeric(normalised_query):
        if len(query.split()) >= min_word_length:
            logger.debug("Matched: {} ---> {}".format(query, name))
            return name.upper()

    if possibles:
        for poss in possibles:
            logger.info("{}".format("Possible Match: {} ---> {}".format(query, poss)))
    return None
