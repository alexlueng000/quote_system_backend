USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS drop_column_if_exists;

DELIMITER //
CREATE PROCEDURE drop_column_if_exists(
  IN table_name_value VARCHAR(64),
  IN column_name_value VARCHAR(64)
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND COLUMN_NAME = column_name_value
  ) THEN
    SET @alter_sql = CONCAT('ALTER TABLE `', table_name_value, '` DROP COLUMN `', column_name_value, '`');
    PREPARE alter_statement FROM @alter_sql;
    EXECUTE alter_statement;
    DEALLOCATE PREPARE alter_statement;
  END IF;
END//
DELIMITER ;

CALL drop_column_if_exists('jurisdictions', 'source_note');
CALL drop_column_if_exists('jurisdictions', 'standard_code');

DROP PROCEDURE IF EXISTS drop_column_if_exists;
