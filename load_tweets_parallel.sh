#!/bin/sh

files='/data/tweets/geoTwitter21-01-01.zip
/data/tweets/geoTwitter21-01-02.zip
/data/tweets/geoTwitter21-01-03.zip
/data/tweets/geoTwitter21-01-04.zip
/data/tweets/geoTwitter21-01-05.zip
/data/tweets/geoTwitter21-01-06.zip
/data/tweets/geoTwitter21-01-07.zip
/data/tweets/geoTwitter21-01-08.zip
/data/tweets/geoTwitter21-01-09.zip
/data/tweets/geoTwitter21-01-10.zip
/data/tweets/geoTwitter21-01-11.zip
/data/tweets/geoTwitter21-01-12.zip
/data/tweets/geoTwitter21-01-13.zip
/data/tweets/geoTwitter21-01-14.zip
/data/tweets/geoTwitter21-01-15.zip'

echo '================================================================================'
echo 'load full dataset' 
echo '================================================================================'
time sh -c "echo '$files' | parallel -j 3 python3 -u load_tweets_batch.py --db=postgresql://hello_flask:hello_flask@localhost:2079/hello_flask_dev --inputs={}"
