USE quote_system;

ALTER TABLE customers
  MODIFY customer_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY customer_level VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';

UPDATE customers
SET customer_type = CONVERT(UNHEX('E4BC81E4B89A') USING utf8mb4)
WHERE customer_type = ''
   OR HEX(customer_type) NOT IN (
     'E4BC81E4B89A',
     'E4B8AAE4BABA',
     'E5BE8BE68980',
     'E4BBA3E79086E69CBAE69E84',
     'E585B6E4BB96'
   );

UPDATE customers
SET customer_level = CONVERT(UNHEX('E699AEE9809A') USING utf8mb4)
WHERE customer_level = ''
   OR HEX(customer_level) NOT IN (
     'E699AEE9809A',
     'E9878DE782B9',
     'E68898E795A5',
     'E69A82E5819C'
   );

UPDATE customers
SET customer_level = CONVERT(UNHEX('E9878DE782B9') USING utf8mb4)
WHERE customer_no = 'C20260606-ZYIP-DEMO';
