#!/usr/bin/python3

import psycopg2
import sqlalchemy
import os
import datetime
import zipfile
import io
import json

def remove_nulls(s):
    if s is None:
        return None
    else:
        return s.replace('\x00','\\x00')

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def _bulk_insert_sql(table, rows):
    if not rows:
        raise ValueError('Must be at least one dictionary in the rows variable')
    else:
        keys = set(rows[0].keys())
        for row in rows:
            if set(row.keys()) != keys:
                raise ValueError('All dictionaries must contain the same keys')

    sql = (f'''
    INSERT INTO {table}
        ('''
        +
        ','.join(keys)
        +
        ''')
        VALUES
        '''
        +
        ','.join([ '('+','.join([f':{key}{i}' for key in keys])+')' for i in range(len(rows))])
        +
        '''
        ON CONFLICT DO NOTHING
        '''
        )

    binds = { key+str(i):value for i,row in enumerate(rows) for key,value in row.items() }
    return (' '.join(sql.split()), binds)


def bulk_insert(connection, table, rows):
    if len(rows)==0:
        return
    sql, binds = _bulk_insert_sql(table, rows)
    res = connection.execute(sqlalchemy.sql.text(sql), binds)


def insert_tweets(connection, tweets, batch_size=1000):
    for i,tweet_batch in enumerate(batch(tweets, batch_size)):
        print(datetime.datetime.now(),'insert_tweets i=',i)
        _insert_tweets(connection, tweet_batch)


def _insert_tweets(connection,input_tweets):
    users = []
    tweets = []

    for tweet in input_tweets:
        users.append({
            'id_users':tweet['user']['id'],
            'created_at':tweet['user']['created_at'],
            'screen_name':remove_nulls(tweet['user']['screen_name']),
            'name':remove_nulls(tweet['user']['name']),
            })

        try:
            text = tweet['extended_tweet']['full_text']
        except:
            text = tweet['text']

        # Get first media URL if it exists
        media_filename = None
        try:
            media = tweet['extended_tweet']['extended_entities']['media']
        except KeyError:
            try:
                media = tweet['extended_entities']['media']
            except KeyError:
                media = []
        
        if len(media) > 0:
            media_filename = media[0]['media_url']

        tweets.append({
            'id_tweets':tweet['id'],
            'id_users':tweet['user']['id'],
            'created_at':tweet['created_at'],
            'text':remove_nulls(text),
            'media_filename':media_filename,
            })

    with connection.begin() as trans:
        bulk_insert(connection, 'users', users)
        
        if len(tweets) > 0:
            sql = sqlalchemy.sql.text('''
            INSERT INTO tweets
                (id_tweets, id_users, created_at, text, media_filename, text_tokens)
                VALUES
                '''
                +
                ','.join([f"(:id_tweets{i}, :id_users{i}, :created_at{i}, :text{i}, :media_filename{i}, to_tsvector('english', :text{i}))" for i in range(len(tweets))])
                +
                '''
                ON CONFLICT DO NOTHING
                '''
                )
            res = connection.execute(sql, { key+str(i):value for i,tweet in enumerate(tweets) for key,value in tweet.items() })


if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--db',required=True)
    parser.add_argument('--inputs',nargs='+',required=True)
    parser.add_argument('--batch_size',type=int,default=1000)
    args = parser.parse_args()

    engine = sqlalchemy.create_engine(args.db, connect_args={
        'application_name': 'load_tweets_batch.py --inputs '+' '.join(args.inputs),
        })
    connection = engine.connect()

    for filename in sorted(args.inputs, reverse=True):
        with zipfile.ZipFile(filename, 'r') as archive:
            print(datetime.datetime.now(),filename)
            for subfilename in sorted(archive.namelist(), reverse=True):
                with io.TextIOWrapper(archive.open(subfilename)) as f:
                    tweets = []
                    for i,line in enumerate(f):
                        tweet = json.loads(line)
                        tweets.append(tweet)
                    insert_tweets(connection,tweets,args.batch_size)
