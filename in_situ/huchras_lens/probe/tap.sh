#!/bin/bash
# usage: tap.sh URL "ADQL" -> csv on stdout (Mozilla UA, public endpoints only)
curl -s -m 120 -A "$CLAUDE_UA" "$1" --data-urlencode "REQUEST=doQuery" --data-urlencode "LANG=ADQL" --data-urlencode "FORMAT=csv" --data-urlencode "QUERY=$2"
