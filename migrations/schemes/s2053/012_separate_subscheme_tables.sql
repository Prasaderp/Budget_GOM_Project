-- Migration: 012_separate_subscheme_tables.sql
-- Status: OBSOLETE - scheme-specific tables now created directly by ORM
-- Tables like budget_post_details_20530028, budget_post_details_20530162 etc.
-- are created by SQLAlchemy's Base.metadata.create_all() from model definitions.
-- Indexes and constraints are defined in the model's __table_args__.

SELECT 1;
