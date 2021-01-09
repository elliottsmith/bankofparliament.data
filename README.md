# bankofparliament.data



Python tools to download data on members of parliament and extract entities, relationships and monetary values.


Extracted data can then be used to populate a Neo4J graph database.


Generates the data powering [https://bankofparliament.co.uk/](https://bankofparliament.co.uk/)


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


```

cd bankofparliament.data

virtualenv env

source env/bin/activate

pip install -r requirements.txt

```



## Executable Scripts



`source setup.sh`



To download the initial dataset



`bop_download_data`



To convert initial dataset to csv entities and relationship files



`bop_convert_data_to_csv -m data/generated/{date}/members.json`



Extract named entities from csv data and output to new files



`bop_extract -e data/generated/{date}/entities.csv -r data/generated/{date}/relationships.csv`



The `bop_extract` tool also takes an optional argument `--custom_entities` which greatly improves accuracy and coverage. A sample file is included in the data/custom directory.



`bop_extract -e data/generated/{date}/entities.csv -r data/generated/{date}/relationships.csv -c data/custom/default_custom_entities.csv`



Create Neo4J database from extracted entities and relationship csv data



`bop_create_db -e data/generated/{date}/extracted/entities.csv -r data/generated/{date}/extracted/relationships.csv`
