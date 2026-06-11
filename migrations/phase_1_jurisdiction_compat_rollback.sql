USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS drop_fk_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;
DROP PROCEDURE IF EXISTS drop_column_if_exists;

DELIMITER //
CREATE PROCEDURE drop_fk_if_exists(
  IN table_name_value VARCHAR(64),
  IN constraint_name_value VARCHAR(64)
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND CONSTRAINT_NAME = constraint_name_value
      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
  ) THEN
    SET @alter_sql = CONCAT('ALTER TABLE `', table_name_value, '` DROP FOREIGN KEY `', constraint_name_value, '`');
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

CALL drop_fk_if_exists('quotation_openings', 'fk_openings_jurisdiction');
CALL drop_fk_if_exists('quotation_items', 'fk_qi_jurisdiction');
CALL drop_fk_if_exists('quotations', 'fk_quotations_jurisdiction');
CALL drop_fk_if_exists('quotation_draft_items', 'fk_qdi_jurisdiction');
CALL drop_fk_if_exists('special_rules', 'fk_special_rules_jurisdiction');
CALL drop_fk_if_exists('fx_tax_rules', 'fk_fx_tax_rules_jurisdiction');
CALL drop_fk_if_exists('language_rules', 'fk_language_rules_jurisdiction');
CALL drop_fk_if_exists('entity_type_rules', 'fk_etr_jurisdiction');
CALL drop_fk_if_exists('country_path_rules', 'fk_cpr_jurisdiction');
CALL drop_fk_if_exists('fee_rules', 'fk_fee_rules_jurisdiction');
CALL drop_fk_if_exists('countries', 'fk_countries_jurisdiction');

CALL drop_index_if_exists('quotation_openings', 'idx_openings_jurisdiction_stats');
CALL drop_index_if_exists('quotation_items', 'idx_qi_jurisdiction_opening');
CALL drop_index_if_exists('quotations', 'idx_quotations_jurisdiction');
CALL drop_index_if_exists('quotation_draft_items', 'idx_qdi_jurisdiction');
CALL drop_index_if_exists('special_rules', 'idx_special_rules_jurisdiction');
CALL drop_index_if_exists('fx_tax_rules', 'idx_fx_tax_rules_jurisdiction');
CALL drop_index_if_exists('language_rules', 'idx_language_rules_jurisdiction');
CALL drop_index_if_exists('entity_type_rules', 'idx_entity_type_rules_jurisdiction');
CALL drop_index_if_exists('country_path_rules', 'idx_country_path_rules_jurisdiction');
CALL drop_index_if_exists('fee_rules', 'idx_fee_rules_jurisdiction_match');
CALL drop_index_if_exists('countries', 'idx_countries_jurisdiction_id');

CALL drop_column_if_exists('translation_schemes', 'applicable_jurisdictions_json');
CALL drop_column_if_exists('framework_agreements', 'covered_jurisdictions_json');
CALL drop_column_if_exists('quotation_openings', 'jurisdiction_id');
CALL drop_column_if_exists('quotation_items', 'jurisdiction_id');
CALL drop_column_if_exists('quotations', 'jurisdiction_ids_json');
CALL drop_column_if_exists('quotations', 'jurisdiction_id');
CALL drop_column_if_exists('quotation_draft_items', 'jurisdiction_id');
CALL drop_column_if_exists('special_rules', 'jurisdiction_id');
CALL drop_column_if_exists('fx_tax_rules', 'jurisdiction_id');
CALL drop_column_if_exists('language_rules', 'jurisdiction_id');
CALL drop_column_if_exists('entity_type_rules', 'jurisdiction_id');
CALL drop_column_if_exists('country_path_rules', 'jurisdiction_id');
CALL drop_column_if_exists('fee_rules', 'jurisdiction_id');
CALL drop_column_if_exists('countries', 'jurisdiction_id');

DROP TABLE IF EXISTS country_jurisdiction_map;
DROP TABLE IF EXISTS jurisdictions;

DROP PROCEDURE IF EXISTS drop_fk_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;
DROP PROCEDURE IF EXISTS drop_column_if_exists;
