set -e # fail on errors
set -x # print commands

apt-get update

bash scripts/install-storm.bash
bash scripts/install-stormpy.bash
bash scripts/install-pric3.bash
