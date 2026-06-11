USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS drop_index_if_exists;
DROP PROCEDURE IF EXISTS drop_column_if_exists;

DELIMITER //
CREATE PROCEDURE drop_index_if_exists(
  IN table_name_value VARCHAR(64),
  IN index_name_value VARCHAR(64)
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND INDEX_NAME = index_name_value
  ) THEN
    SET @alter_sql = CONCAT('ALTER TABLE `', table_name_value, '` DROP INDEX `', index_name_value, '`');
    PREPARE alter_statement FROM @alter_sql;
    EXECUTE alter_statement;
    DEALLOCATE PREPARE alter_statement;
  END IF;
END//

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

CALL drop_index_if_exists('jurisdictions', 'idx_jurisdictions_deleted_enabled');
CALL drop_index_if_exists('countries', 'idx_countries_deleted_enabled');

CALL drop_column_if_exists('jurisdictions', 'delete_reason');
CALL drop_column_if_exists('jurisdictions', 'deleted_by');
CALL drop_column_if_exists('jurisdictions', 'deleted_at');
CALL drop_column_if_exists('jurisdictions', 'is_deleted');

CALL drop_column_if_exists('countries', 'delete_reason');
CALL drop_column_if_exists('countries', 'deleted_by');
CALL drop_column_if_exists('countries', 'deleted_at');
CALL drop_column_if_exists('countries', 'is_deleted');

DROP PROCEDURE IF EXISTS drop_index_if_exists;
DROP PROCEDURE IF EXISTS drop_column_if_exists;
