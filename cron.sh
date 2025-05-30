#!/bin/bash

echo "starting cron job for script ./website/update.py in 60s"
sleep 300
while true; do
  ./website/make_website.sh
  wait
  sleep 36000
done
