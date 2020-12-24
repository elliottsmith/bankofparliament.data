source env/bin/activate
export PYTHONPATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )/lib:$PYTHONPATH
export PATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )/bin:$PATH
