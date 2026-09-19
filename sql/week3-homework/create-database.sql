\set ON_ERROR_STOP on

-- PostgreSQL 18 / psql
-- Run while connected to the existing bigdata database.
SELECT 'CREATE DATABASE week3_hw OWNER bigdata'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'week3_hw'
)\gexec
