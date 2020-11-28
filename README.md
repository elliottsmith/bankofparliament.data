# bankofparliament.data
Python tools to download data on members of parliament and extract meaning, entities and relationships.

## Prerequisites
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
   pip install spacy

Alternatively, a virtual env script is provided:

    cd bankofparliament.data
    ./bin/bop_create_virtualenv
    source setup.sh

## Executable Scripts

To download the initial dataset

    ./bin/bop_download_data

To convert initial dataset to csv entities and relationship files

    ./bin/bop_convert_data_to_csv --members=data/members/{date}/{date}.json
