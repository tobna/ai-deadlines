#!/bin/bash

echo "starting cron job for script ./website/update.py"
while true; do
  ./website/make_website.sh
  wait
  sleep 36000
done
