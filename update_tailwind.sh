#!/bin/sh

# The frontend stylesheet is now a hand-authored, self-contained design system
# (aideadlines/styles.css). There is no Tailwind build step anymore: the served
# file (styles.tailwind.css, referenced by index.html) is just a verbatim copy.
# This script keeps that copy in sync so the filename expected by the site and
# make_website.sh stays valid.

cp aideadlines/styles.css aideadlines/styles.tailwind.css
