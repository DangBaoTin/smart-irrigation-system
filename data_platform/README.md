psql -h localhost -p 5432 -U admin -d sis
psql -h localhost -p 5432 -U admin -d mydb

\l: list database
\c: check used database
\c <db_name>: switch db
\dt: list all tables


create table if not exists weather_state (
    id varchar(20) primary key,
    place_id int not null,
    temperature numeric(5,2),
    humidity numeric(5,2),
    rain numeric(5,2),
    evapo numeric(5,2),
    wind numeric(5,2),
    s_moist numeric(5,2)
);

create table if not exists place (
    id serial primary key,
    name varchar(255) not null,
    lat decimal(10, 6) not null,
    lon decimal(10, 6) not null
);

