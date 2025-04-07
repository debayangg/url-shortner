-- Table to store codes with their associated links
create table if not exists url (
    code text primary key,
    link text not null );

-- Table to store settings like the current max value
create table if not exists settings (
    key text primary key,
    value bigint not null );