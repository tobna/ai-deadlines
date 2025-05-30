#!/bin/bash

BASEDIR=$(dirname $0)
echo "starting cron job for script ${BASEDIR}/update.py"
while true; do
  python3 ${BASEDIR}/update.py
  sleep 60 * 60 * 10
done
