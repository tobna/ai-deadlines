#!/bin/bash

echo "starting cron job for script ./website/update.py"
while true; do
  ./website/make_website.sh
  wait
  sleep 60 * 60 * 10
done
