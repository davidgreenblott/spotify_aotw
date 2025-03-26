#!/bin/bash

set -e # stop on error
set -u # raise error if variable is unset
set -o pipefail #fail if any prior step failed

echo "Running add_album.py"

python src/add_album.py --url "$1"