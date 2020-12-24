# bankofparliament.data



Python tools to download data on members of parliament and extract entities and relationships.



Extracted data can then be used to populate a Neo4J graph database.



## Prerequisites



### Neo4J database



You will need a Neo4j database. Instances can be run locally, in a service such as AWS, Azure or GrapheneDB or alternatively as a [free sandbox](https://neo4j.com/sandbox/).



Create and add your Neo4J information to a dotenv (.env) file. An example file can be found, `.env.example`.



### Api Keys



You will need the following api keys in order to run all tools contained in this repository



-  [theyworkforyou](https://www.theyworkforyou.com/api/)

-  [companies house](https://developer.company-information.service.gov.uk/api/docs/index/gettingStarted.html#createaccount)



Add these to your `.env` file.



### Python 3 Packages



`pip install lxml, bs4, requests, numpy, pandas, tabula-py, spacy, neo4j, scraperwiki, python-dotenv`



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


- family lobbyists - need relationship to gov not back to relation

- 'reconcile_findthatcharity_entity_by_id' util function

- reconcile human entities to records in opencorporates

- add ability to enter findthatcharity url when in prompt mode

- spacy model for recurring and single payments

- spacy model for custom / known entities

- convert pattern identifiers to custom entities
