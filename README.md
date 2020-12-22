# bankofparliament.data

Python tools to download data on members of parliament and extract entities and relationships.

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

-  [theyworkforyou](https://www.theyworkforyou.com/api/)
-  [companies house](https://developer.company-information.service.gov.uk/api/docs/index/gettingStarted.html#createaccount)

Create and add your keys to this file: `$HOME/.apikeys/apikeys.py`

THEYWORKFORYOU_APIKEY = 'your_theyworkforyou_api_key'
COMPANIES_HOUSE_APIKEY = 'your_companies_house_api_key'

### Python 3 Packages

`pip install lxml, bs4, requests, numpy, pandas, tabula-py, spacy, neo4j, scraperwiki`

Alternatively,

```
cd bankofparliament.data
virtualenv env
source env/bin/activate
pip install -r requirements.txt
```

## Executable Scripts

`source setup.sh`

To download the initial dataset

`./bin/bop_download_data`

To convert initial dataset to csv entities and relationship files

`./bin/bop_convert_data_to_csv --members=data/generated/{date}/members.json`

Extract named entities from csv data and output to new files

`./bin/bop_ner_extract --entities=data/generated/{date}/entities.csv --relationships=data/generated/{date}/relationships.csv`

The `bop_ner_extract` tool also takes an optional argument `--custom_entities` which greatly improves accuracy and coverage. A sample file is included in the data/custom directory.

`./bin/bop_ner_extract --entities=data/generated/{date}/entities.csv --relationships=data/generated/{date}/relationships.csv --custom_entities=data/custom/default_custom_entities.csv`

Create Neo4J database from extracted entities and relationship csv data

`./bin/bop_create_db --entities=data/generated/{date}/extracted/entities.csv --relationships=data/generated/{date}/extracted/relationships.csv`

## TODO

- when checking aliases, stop substring matching, must have space either side or a preceding a space if last word

- family lobbists - need relationship to gov not back to relation

- 'reconcile_findthatcharity_entity_by_id' util function