#!/bin/sh

wget -nc https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.8/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64

rm -f aideadlines/styles.tailwind.css
./tailwindcss-linux-x64 -i aideadlines/styles.css -o aideadlines/styles.tailwind.css --content "./*.{html,js}" -m
