#!/bin/sh

echo "updating and creating website"

ls

echo "1. update conference data"
python3 update.py

echo "2. update plausible script"
wget https://plausible.nauen-it.de/js/script.js -O src/plausible.js

echo "3. copy files over"
cp -r src/* html/

echo "4. compress files: gzip"
find html -type f \( -name '*.json' -o -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.ttf' -o -name '*.woff2' -o -name '*.xml' -o -name '*.svg' -o -name '*.jpg' -o -name '*.webp' \) -exec gzip -v -k -f --best {} \;

echo "5. remove changes to git repo"
git stash
