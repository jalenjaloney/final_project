CREATE EXTENSION rum;

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE users (
    id_users BIGSERIAL PRIMARY KEY,
    screen_name TEXT,
    name TEXT,
    created_at TIMESTAMPTZ
);

CREATE TABLE credentials (
    id_credentials SERIAL PRIMARY KEY,
    id_users BIGINT REFERENCES users(id_users),
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX credentials_username_idx ON credentials(username);

CREATE TABLE tweets (
    id_tweets BIGINT PRIMARY KEY,
    id_users BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    text TEXT NOT NULL,
    media_filename TEXT,
    text_tokens tsvector,
    FOREIGN KEY (id_users) REFERENCES users(id_users)
);
CREATE INDEX tweets_created_at_idx ON tweets(created_at DESC);
CREATE INDEX tweets_id_users_idx ON tweets(id_users);
CREATE INDEX tweets_rum_idx ON tweets USING rum(text_tokens rum_tsvector_ops);

COMMIT;
