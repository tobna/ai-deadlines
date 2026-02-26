#!/bin/sh

echo "updating and creating website"

ls

echo "1. update conference data"
python3 update.py

# echo "2. update tailwindcss"
# ./update_tailwind.sh

echo "3. copy files over"
mkdir -p html/data
cp aideadlines/*.html aideadlines/*.js aideadlines/*.css html/
cp aideadlines/data/*.json html/data/
cp aideadlines/*.ico aideadlines/*.svg aideadlines/*.png aideadlines/site.webmanifest aideadlines/robots.txt aideadlines/sitemap.xml html/

echo "4. compress files: gzip"
find html -type f \( -name '*.json' -o -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.ttf' -o -name '*.woff2' -o -name '*.xml' -o -name '*.svg' -o -name '*.jpg' -o -name '*.webp' \) -exec gzip -v -k -f --best {} \;
