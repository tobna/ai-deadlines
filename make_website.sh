#!/bin/bash

BASEDIR=$(dirname $0)
echo "updating and creating website"

echo "goto /website"
cd /website
ls

echo "1. update conference data"
python3 ${BASEDIR}/update.py

echo "2. compress files: gzip"

find src -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.ttf' -o -name '*.woff2' -o -name '*.xml' -o -name '*.svg' -o -name '*.jpg' -o -name '*.webp' \) -exec gzip -v -k -f --best {} \;

echo "3. copy files over"
cp -r src /usr/share/nginx/html/

echo "4. remove changes to git repo"
git stash
