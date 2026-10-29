-- Apply once when provisioning or upgrading: psql "$DATABASE_URL" -f schema.sql
-- Existing rows and balances are preserved. Timestamps are UTC.
BEGIN;
CREATE TABLE IF NOT EXISTS servers (server_id BIGINT PRIMARY KEY, prefix TEXT);
CREATE TABLE IF NOT EXISTS greetings (
    user_id BIGINT PRIMARY KEY, gm BOOLEAN NOT NULL DEFAULT FALSE,
    ga BOOLEAN NOT NULL DEFAULT FALSE, ge BOOLEAN NOT NULL DEFAULT FALSE,
    gn BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS analytics (
    id BIGSERIAL PRIMARY KEY, command TEXT NOT NULL, server_id BIGINT,
    user_id BIGINT NOT NULL, time_of_command TIMESTAMP NOT NULL
);
-- Direct messages have no guild ID.
ALTER TABLE analytics ALTER COLUMN server_id DROP NOT NULL;
CREATE TABLE IF NOT EXISTS bollywood_points (
    user_id BIGINT PRIMARY KEY, points INT DEFAULT 0, rounds INT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS plotster_points (
    user_id BIGINT PRIMARY KEY, points INT DEFAULT 0, rounds INT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS points (user_id BIGINT PRIMARY KEY, coins BIGINT NOT NULL DEFAULT 0);
ALTER TABLE points ALTER COLUMN coins TYPE BIGINT;
CREATE INDEX IF NOT EXISTS pippo_coin_ranking ON points (coins DESC, user_id);
CREATE INDEX IF NOT EXISTS pippo_movie_ranking ON bollywood_points (points DESC, user_id) WHERE points IS NOT NULL;
CREATE INDEX IF NOT EXISTS pippo_plotster_ranking ON plotster_points (points DESC, user_id) WHERE points IS NOT NULL;
CREATE TABLE IF NOT EXISTS characters (
    user_id BIGINT PRIMARY KEY, show_name TEXT, cartoon_character TEXT,
    dog_breed TEXT, cat_breed TEXT
);
COMMIT;
