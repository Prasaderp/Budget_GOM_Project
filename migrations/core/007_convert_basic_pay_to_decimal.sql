-- Migration: Convert basic_pay column from BigInteger to Numeric(10,1) to support decimal values
-- This allows storing basic pay in thousands format (e.g., 67.1) instead of full amounts

-- Step 1: Convert existing integer values to decimal format (thousands)
-- If value >= 1000, convert to thousands: round(value/100)/10
-- Otherwise keep as is (already in thousands or zero)
UPDATE budget_post_details
SET basic_pay = CASE 
    WHEN basic_pay >= 1000 THEN ROUND(ROUND(basic_pay::numeric / 100) / 10, 1)
    ELSE basic_pay::numeric
END;

-- Step 2: Change column type to Numeric(10,1)
ALTER TABLE budget_post_details 
ALTER COLUMN basic_pay TYPE NUMERIC(10,1) USING basic_pay::numeric(10,1);

-- Step 3: Update default value to numeric format
ALTER TABLE budget_post_details 
ALTER COLUMN basic_pay SET DEFAULT 0;

-- Step 4: Update server default
ALTER TABLE budget_post_details 
ALTER COLUMN basic_pay SET DEFAULT 0;

