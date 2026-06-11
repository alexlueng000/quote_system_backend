USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS drop_column_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;

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
DELIMITER ;

CALL drop_index_if_exists('jurisdictions', 'idx_jurisdictions_default_office');
CALL drop_column_if_exists('jurisdictions', 'default_office_source_note');
CALL drop_column_if_exists('jurisdictions', 'default_office_type');
CALL drop_column_if_exists('jurisdictions', 'default_office_name_en');
CALL drop_column_if_exists('jurisdictions', 'default_office_name_cn');
CALL drop_column_if_exists('jurisdictions', 'default_office_code');
CALL drop_column_if_exists('jurisdictions', 'default_office_jurisdiction_id');

UPDATE jurisdiction_data_source_registry
SET is_active = 0,
    review_status = 'deprecated'
WHERE source_id IN ('WIPO_IP_OFFICES_DIRECTORY', 'UN_M49', 'BUSINESS_REGION_SOURCE');

UPDATE jurisdiction_reference_registry
SET geo_region = 'Other',
    default_business_economic_regions_json = JSON_ARRAY('OTHER'),
    review_status = 'pending_review'
WHERE reference_id = 'ref-co'
  AND jurisdiction_id IS NULL;

UPDATE jurisdiction_reference_registry
SET geo_region = 'Other',
    default_business_economic_regions_json = JSON_ARRAY('OTHER'),
    review_status = 'pending_review'
WHERE reference_id = 'ref-ch'
  AND jurisdiction_id IS NULL;

DROP PROCEDURE IF EXISTS drop_column_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;
