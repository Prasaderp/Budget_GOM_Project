-- Migration: 007_convert_basic_pay_to_decimal.sql
-- Status: OBSOLETE - scheme tables now created by ORM with correct Numeric type
-- The scheme-specific models define basic_pay as Numeric(10,1) directly.

SELECT 1;
