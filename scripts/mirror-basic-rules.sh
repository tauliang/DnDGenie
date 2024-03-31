#!/usr/bin/env bash

wget -r --accept-regex "compendium/rules/basic-rules/" \
   --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
   "https://www.dndbeyond.com/sources/basic-rules"
