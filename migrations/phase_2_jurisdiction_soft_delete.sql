USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;

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

CREATE PROCEDURE add_index_if_missing(
  IN table_name_value VARCHAR(64),
  IN index_name_value VARCHAR(64),
  IN index_definition_value TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND INDEX_NAME = index_name_value
  ) THEN
    SET @alter_sql = CONCAT('ALTER TABLE `', table_name_value, '` ADD ', index_definition_value);
    PREPARE alter_statement FROM @alter_sql;
    EXECUTE alter_statement;
    DEALLOCATE PREPARE alter_statement;
  END IF;
END//
DELIMITER ;

CALL add_column_if_missing('countries', 'is_deleted', '`is_deleted` TINYINT(1) NOT NULL DEFAULT 0 AFTER `enabled`');
CALL add_column_if_missing('countries', 'deleted_at', '`deleted_at` DATETIME NULL AFTER `is_deleted`');
CALL add_column_if_missing('countries', 'deleted_by', '`deleted_by` VARCHAR(255) NULL AFTER `deleted_at`');
CALL add_column_if_missing('countries', 'delete_reason', '`delete_reason` VARCHAR(500) NULL AFTER `deleted_by`');

CALL add_column_if_missing('jurisdictions', 'is_deleted', '`is_deleted` TINYINT(1) NOT NULL DEFAULT 0 AFTER `is_enabled`');
CALL add_column_if_missing('jurisdictions', 'deleted_at', '`deleted_at` DATETIME NULL AFTER `is_deleted`');
CALL add_column_if_missing('jurisdictions', 'deleted_by', '`deleted_by` VARCHAR(255) NULL AFTER `deleted_at`');
CALL add_column_if_missing('jurisdictions', 'delete_reason', '`delete_reason` VARCHAR(500) NULL AFTER `deleted_by`');

CALL add_index_if_missing('countries', 'idx_countries_deleted_enabled', 'KEY `idx_countries_deleted_enabled` (`is_deleted`, `enabled`, `display_order`, `code`)');
CALL add_index_if_missing('jurisdictions', 'idx_jurisdictions_deleted_enabled', 'KEY `idx_jurisdictions_deleted_enabled` (`is_deleted`, `is_enabled`, `display_order`, `internal_code`)');

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
