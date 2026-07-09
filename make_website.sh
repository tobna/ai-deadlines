#!/bin/sh

echo "updating and creating website"

ls

echo "1. update conference data"
# tee shows the run live on the console and saves the raw colored stream for rendering below.
python3 update.py 2>&1 | tee status.ansi

# echo "2. update tailwindcss"
# ./update_tailwind.sh

echo "2. copy files over"
mkdir -p html/data html/fonts
cp aideadlines/*.html aideadlines/*.js aideadlines/*.css html/
cp aideadlines/data/*.json html/data/
cp aideadlines/fonts/*.woff2 html/fonts/
cp aideadlines/*.ico aideadlines/*.svg aideadlines/*.png aideadlines/site.webmanifest aideadlines/robots.txt aideadlines/sitemap.xml html/

# Render the colored run into the served status page (served at /status.html).
# The plain "=== PIPELINE OK ===" marker survives verbatim for the Uptime Kuma keyword check.
echo "3. render status page"
python3 aideadlines/ansi_to_html.py html/status.html <status.ansi

echo "4. compress files: gzip"
find html -type f \( -name '*.json' -o -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.ttf' -o -name '*.woff2' -o -name '*.xml' -o -name '*.svg' -o -name '*.jpg' -o -name '*.webp' \) -exec gzip -v -k -f --best {} \;
