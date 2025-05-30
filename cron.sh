#!/bin/bash

BASEDIR=$(dirname $0)
echo "starting cron job for script ${BASEDIR}/update.py"
while true; do
  /bin/bash ${BASEDIR}/make_website.sh
  sleep 60 * 60 * 10
done
