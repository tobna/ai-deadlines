#!/bin/sh

wget -nc https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.8/tailwindcss-linux-x64

./tailwindcss-linux-x64 -i src/styles.css -o src/styles.tailwind.css --content "./*.{html,js}" -m
