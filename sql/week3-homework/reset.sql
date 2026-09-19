\set ON_ERROR_STOP on

-- PostgreSQL 18 / psql
-- This removes only the homework-owned schemas inside week3_hw.
-- Run setup.sql afterward to rebuild them.
DROP SCHEMA IF EXISTS gold CASCADE;
DROP SCHEMA IF EXISTS silver CASCADE;
DROP SCHEMA IF EXISTS bronze CASCADE;
