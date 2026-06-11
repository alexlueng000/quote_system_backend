USE quote_system;
SET NAMES utf8mb4;

-- Rollback note:
-- This rollback is intended for development or acceptance environments.
-- `jurisdictions.is_deleted` is a cross-module compatibility field. It is not
-- dropped by default because removing it in a shared environment can break
-- readers that already depend on disabled/deleted jurisdiction filtering.
-- To drop it in a disposable environment, set @allow_drop_jurisdiction_is_deleted = 1.

SET @allow_drop_jurisdiction_is_deleted = 0;

DELIMITER //

DROP PROCEDURE IF EXISTS drop_column_if_exists //
CREATE PROCEDURE drop_column_if_exists(
  IN table_name_value VARCHAR(128),
  IN column_name_value VARCHAR(128)
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND COLUMN_NAME = column_name_value
  ) THEN
    SET @ddl = CONCAT('ALTER TABLE `', table_name_value, '` DROP COLUMN `', column_name_value, '`');
    PREPARE stmt FROM @ddl;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END //

DROP PROCEDURE IF EXISTS drop_index_if_exists //
CREATE PROCEDURE drop_index_if_exists(
  IN table_name_value VARCHAR(128),
  IN index_name_value VARCHAR(128)
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND INDEX_NAME = index_name_value
  ) THEN
    SET @ddl = CONCAT('ALTER TABLE `', table_name_value, '` DROP INDEX `', index_name_value, '`');
    PREPARE stmt FROM @ddl;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END //

DELIMITER ;

UPDATE ip_system_master s
JOIN ip_system_p0_state_backup b
  ON b.backup_name = 'p0_first_batch_20260607'
 AND b.entity_type = 'ip_system_master'
 AND b.entity_id = s.system_id
SET s.is_active = COALESCE(b.is_active, s.is_active),
    s.remark = b.remark;

UPDATE ip_system_business_domain d
JOIN ip_system_p0_state_backup b
  ON b.backup_name = 'p0_first_batch_20260607'
 AND b.entity_type = 'ip_system_business_domain'
 AND b.entity_id = d.system_id
 AND b.business_domain = d.business_domain
SET d.is_enabled = COALESCE(b.is_enabled, d.is_enabled),
    d.remark = b.remark;

DELETE FROM ip_system_source_config
WHERE system_id = 'ip-system-madrid'
  AND NOT EXISTS (
    SELECT 1
    FROM ip_system_p0_state_backup
    WHERE backup_name = 'p0_first_batch_20260607'
      AND entity_type = 'ip_system_master'
      AND entity_id = 'ip-system-madrid'
  );

DELETE FROM ip_system_business_domain
WHERE system_id = 'ip-system-madrid'
  AND NOT EXISTS (
    SELECT 1
    FROM ip_system_p0_state_backup
    WHERE backup_name = 'p0_first_batch_20260607'
      AND entity_type = 'ip_system_business_domain'
      AND entity_id = 'ip-system-madrid'
  );

DELETE FROM ip_system_master
WHERE system_id = 'ip-system-madrid'
  AND NOT EXISTS (
    SELECT 1
    FROM ip_system_p0_state_backup
    WHERE backup_name = 'p0_first_batch_20260607'
      AND entity_type = 'ip_system_master'
      AND entity_id = 'ip-system-madrid'
  );

DROP TABLE IF EXISTS ip_system_relation_candidate;

CALL drop_column_if_exists('ip_system_source_config', 'parse_mode');
CALL drop_column_if_exists('ip_system_source_config', 'official_source_name');
CALL drop_column_if_exists('ip_system_source_config', 'source_scope');

CALL drop_index_if_exists('jurisdictions', 'idx_jurisdictions_enabled_deleted');
SET @drop_jurisdiction_is_deleted_sql = IF(
  @allow_drop_jurisdiction_is_deleted = 1,
  'CALL drop_column_if_exists(''jurisdictions'', ''is_deleted'')',
  'SELECT ''jurisdictions.is_deleted retained by rollback safety guard'' AS rollback_note'
);
PREPARE stmt FROM @drop_jurisdiction_is_deleted_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

DROP PROCEDURE IF EXISTS drop_column_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;
