#!/bin/bash

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    echo "Error: Script is executed. Using sourcing of the script: source ${0}"
    exit 1
else
    echo "Info: Sourced, this is good."
fi



. .venv/bin/activate

python3 -m pip install -r requirements.txt
