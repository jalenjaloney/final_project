FROM postgis/postgis:13-3.1

RUN apt-get update && apt-get install -y \
    postgresql-13-rum \
    less \
    make \
    vim

WORKDIR /tmp/db

RUN mkdir /data && chown postgres /data

# Copy schema - numbered to control execution order
COPY schema.sql /docker-entrypoint-initdb.d/01.sql
