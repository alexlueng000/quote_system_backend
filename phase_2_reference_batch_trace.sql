USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS add_column_if_missing;

DELIMITER //
CREATE PROCEDURE add_column_if_missing(
  IN table_name_value VARCHAR(64),
  IN column_name_value VARCHAR(64),
  IN column_definition_value TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND COLUMN_NAME = column_name_value
  ) THEN
    SET @alter_sql = CONCAT('ALTER TABLE `', table_name_value, '` ADD COLUMN ', column_definition_value);
    PREPARE alter_statement FROM @alter_sql;
    EXECUTE alter_statement;
    DEALLOCATE PREPARE alter_statement;
  END IF;
END//
DELIMITER ;

CALL add_column_if_missing('jurisdictions', 'standard_code', '`standard_code` VARCHAR(50) NOT NULL DEFAULT \'\' AFTER `internal_code`');
CALL add_column_if_missing('jurisdictions', 'source_note', '`source_note` VARCHAR(1000) NOT NULL DEFAULT \'\' AFTER `source_version`');

UPDATE jurisdictions
SET standard_code = internal_code
WHERE standard_code = '';

DROP PROCEDURE IF EXISTS add_column_if_missing;
