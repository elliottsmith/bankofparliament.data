source env/bin/activate
export PYTHONPATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )/lib:$HOME/.apikeys:$PYTHONPATH
export PATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )/bin:$PATH
