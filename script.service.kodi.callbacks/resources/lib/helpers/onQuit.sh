#!/usr/bin/env bash
while kill -0 $1 > /dev/null 2>&1
do
    sleep 0.2
done
# insert your code here