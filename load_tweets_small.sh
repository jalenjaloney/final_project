#!/bin/sh

# Load small dataset for debugging (first 2 files only)

echo '================================================================================'
echo 'load small dataset for debugging'
echo '================================================================================'
time sh -c 'ls data/* | head -2 | parallel python3 -u load_tweets_batch.py --db=postgresql://hello_flask:hello_flask@localhost:2079/hello_flask_dev --inputs={}'
