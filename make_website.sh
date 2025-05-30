#!/bin/bash

echo "updating and creating website"

echo "goto /website"
cd /website
ls

echo "1. update conference data"
python3 update.py

echo "2. make json files"
python3 data_to_json.py

echo "3. compress files: gzip"

find src -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.ttf' -o -name '*.woff2' -o -name '*.xml' -o -name '*.svg' -o -name '*.jpg' -o -name '*.webp' \) -exec gzip -v -k -f --best {} \;

echo "4. copy files over"
cp -r src/* /usr/share/nginx/html/

echo "5. remove changes to git repo"
git stash
