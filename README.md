# bankofparliament.data
Python tools to download data on members of parliament and extract meaning, entities and relationships.
Extracted data can then be used to populate a Neo4J graph database.

## Prerequisites

### Neo4J database
You will need a Neo4j database. Instances can be run locally, in a service such as AWS, Azure or GrapheneDB or alternatively as a [free sandbox](https://neo4j.com/sandbox/).

Create and add your Neo4J information to this file: `$HOME/.apikeys/apikeys.py`

    NEO4J_HOST = 'localhost'
    NEO4J_PASSWORD = 'password'
    NEO4J_USER = 'neo4j'
    NEO4J_BOLT_PORT = 7687

### Api Keys
You will need the following api keys in order to run all tools contained in this repository
 - [theyworkforyou](https://www.theyworkforyou.com/api/)
 - [companies house](https://developer.company-information.service.gov.uk/api/docs/index/gettingStarted.html#createaccount)

Create and add your keys to this file: `$HOME/.apikeys/apikeys.py`

    THEYWORKFORYOU_APIKEY = 'your_theyworkforyou_api_key'
    COMPANIES_HOUSE_APIKEY = 'your_companies_house_api_key'

### Python 3 Packages
 - pip install lxml
 - pip install bs4
 - pip install nltk
 - pip install requests
 - pip install numpy
 - pip install pandas
 - pip install tabula-py
 - pip install spacy
 - pip install spacy-lookups-data
 - pip install neo4j

Alternatively, a virtual env script is provided:

    cd bankofparliament.data
    ./bin/bop_create_virtualenv
    source setup.sh

## Executable Scripts

To download the initial dataset

    ./bin/bop_download_data

To convert initial dataset to csv entities and relationship files

    ./bin/bop_convert_data_to_csv --members=data/members/{date}/{date}.json

Extract named entities from csv data and output to new _extracted.csv files

    ./bin/bop_ner_extract --entities=data/members/{date}/entities.csv  --relationships=data/members/{date}/relationships.csv

Create Neo4J database from extracted entities and relationship csv data

    ./bin/bop_create_db --entities=data/members/{date}/entities_extracted.csv  --relationships=data/members/{date}/relationships_extracted.csv
