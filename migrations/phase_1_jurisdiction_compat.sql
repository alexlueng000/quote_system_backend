USE quote_system;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
DROP PROCEDURE IF EXISTS add_fk_if_missing;

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

CREATE PROCEDURE add_fk_if_missing(
  IN table_name_value VARCHAR(64),
  IN constraint_name_value VARCHAR(64),
  IN constraint_definition_value TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = table_name_value
      AND CONSTRAINT_NAME = constraint_name_value
      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
  ) THEN
    SET @alter_sql = CONCAT('ALTER TABLE `', table_name_value, '` ADD CONSTRAINT ', constraint_definition_value);
    PREPARE alter_statement FROM @alter_sql;
    EXECUTE alter_statement;
    DEALLOCATE PREPARE alter_statement;
  END IF;
END//
DELIMITER ;

CREATE TABLE IF NOT EXISTS jurisdictions (
  jurisdiction_id VARCHAR(64) PRIMARY KEY,
  internal_code VARCHAR(50) NOT NULL,
  display_code VARCHAR(50) NOT NULL,
  name_cn VARCHAR(100) NOT NULL,
  name_en VARCHAR(150) NOT NULL,
  jurisdiction_type VARCHAR(50) NOT NULL DEFAULT 'single_country',
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  display_order INT NOT NULL DEFAULT 100,
  iso_alpha2 CHAR(2) NULL,
  iso_alpha3 CHAR(3) NULL,
  iso_numeric CHAR(3) NULL,
  un_m49_code CHAR(3) NULL,
  wipo_st3_code VARCHAR(10) NULL,
  source_name VARCHAR(100) NOT NULL DEFAULT '',
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  source_version VARCHAR(100) NOT NULL DEFAULT '',
  last_verified_at DATETIME NULL,
  source_verified TINYINT(1) NOT NULL DEFAULT 0,
  source_verified_at DATETIME NULL,
  source_verified_by VARCHAR(255) NULL,
  manual_override TINYINT(1) NOT NULL DEFAULT 0,
  remarks TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_jurisdictions_internal_code (internal_code),
  UNIQUE KEY uk_jurisdictions_display_code (display_code),
  UNIQUE KEY uk_jurisdictions_iso_alpha2 (iso_alpha2),
  UNIQUE KEY uk_jurisdictions_iso_alpha3 (iso_alpha3),
  UNIQUE KEY uk_jurisdictions_iso_numeric (iso_numeric),
  UNIQUE KEY uk_jurisdictions_un_m49_code (un_m49_code),
  UNIQUE KEY uk_jurisdictions_wipo_st3_code (wipo_st3_code),
  KEY idx_jurisdictions_enabled_order (is_enabled, display_order, internal_code),
  KEY idx_jurisdictions_type (jurisdiction_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS country_jurisdiction_map (
  country_code VARCHAR(20) NOT NULL PRIMARY KEY,
  jurisdiction_id VARCHAR(64) NOT NULL,
  mapping_type VARCHAR(50) NOT NULL DEFAULT 'legacy_country_code',
  is_primary TINYINT(1) NOT NULL DEFAULT 1,
  remarks VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_cjm_jurisdiction (jurisdiction_id),
  CONSTRAINT fk_cjm_country
    FOREIGN KEY (country_code) REFERENCES countries(code),
  CONSTRAINT fk_cjm_jurisdiction
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO jurisdictions (
  jurisdiction_id, internal_code, display_code, name_cn, name_en,
  jurisdiction_type, is_enabled, display_order,
  iso_alpha2, iso_alpha3, iso_numeric, un_m49_code, wipo_st3_code,
  source_name, source_version, manual_override, remarks
)
SELECT
  CONCAT('jur-', c.code),
  c.code,
  CASE c.code WHEN 'EP' THEN 'EPO' ELSE c.code END,
  c.name_cn,
  c.name_en,
  CASE
    WHEN COALESCE(c.country_type, '') = '区域局' THEN 'regional_office'
    WHEN c.code = 'EP' THEN 'regional_office'
    ELSE 'single_country'
  END,
  c.enabled,
  COALESCE(c.display_order, 100),
  CASE c.code WHEN 'US' THEN 'US' WHEN 'JP' THEN 'JP' WHEN 'KR' THEN 'KR' ELSE NULL END,
  CASE c.code WHEN 'US' THEN 'USA' WHEN 'JP' THEN 'JPN' WHEN 'KR' THEN 'KOR' ELSE NULL END,
  CASE c.code WHEN 'US' THEN '840' WHEN 'JP' THEN '392' WHEN 'KR' THEN '410' ELSE NULL END,
  CASE c.code WHEN 'US' THEN '840' WHEN 'JP' THEN '392' WHEN 'KR' THEN '410' ELSE NULL END,
  CASE c.code WHEN 'EP' THEN 'EP' ELSE c.code END,
  'legacy_countries',
  'phase_1_jurisdiction_compat',
  1,
  CONCAT('Backfilled from legacy countries.code=', c.code)
FROM countries c
LEFT JOIN jurisdictions j ON j.jurisdiction_id = CONCAT('jur-', c.code)
WHERE j.jurisdiction_id IS NULL;

INSERT INTO country_jurisdiction_map (
  country_code, jurisdiction_id, mapping_type, is_primary, remarks
)
SELECT
  c.code,
  CONCAT('jur-', c.code),
  'legacy_country_code',
  1,
  'Phase 1 compatibility bridge; legacy country_code remains the active runtime key.'
FROM countries c
LEFT JOIN country_jurisdiction_map m ON m.country_code = c.code
WHERE m.country_code IS NULL;

CALL add_column_if_missing('countries', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL');
CALL add_column_if_missing('jurisdictions', 'source_verified', '`source_verified` TINYINT(1) NOT NULL DEFAULT 0 AFTER `last_verified_at`');
CALL add_column_if_missing('jurisdictions', 'source_verified_at', '`source_verified_at` DATETIME NULL AFTER `source_verified`');
CALL add_column_if_missing('jurisdictions', 'source_verified_by', '`source_verified_by` VARCHAR(255) NULL AFTER `source_verified_at`');
CALL add_column_if_missing('fee_rules', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('country_path_rules', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('entity_type_rules', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('language_rules', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('fx_tax_rules', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('special_rules', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('quotation_draft_items', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('quotations', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('quotations', 'jurisdiction_ids_json', '`jurisdiction_ids_json` JSON NULL AFTER `country_codes_json`');
CALL add_column_if_missing('quotation_items', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('quotation_openings', 'jurisdiction_id', '`jurisdiction_id` VARCHAR(64) NULL AFTER `country_code`');
CALL add_column_if_missing('framework_agreements', 'covered_jurisdictions_json', '`covered_jurisdictions_json` JSON NULL AFTER `covered_countries_json`');
CALL add_column_if_missing('translation_schemes', 'applicable_jurisdictions_json', '`applicable_jurisdictions_json` JSON NULL AFTER `applicable_countries_json`');

UPDATE countries c
JOIN country_jurisdiction_map m ON m.country_code = c.code
SET c.jurisdiction_id = m.jurisdiction_id
WHERE c.jurisdiction_id IS NULL;

UPDATE jurisdictions
SET display_code = CASE internal_code
    WHEN 'EP' THEN 'EPO'
    WHEN 'EM' THEN 'EUIPO'
    WHEN 'WO' THEN 'WIPO'
    WHEN 'PCT' THEN 'PCT'
    ELSE display_code
  END,
  name_cn = CASE internal_code
    WHEN 'EP' THEN '欧洲专利局'
    WHEN 'EM' THEN '欧盟知识产权局'
    WHEN 'WO' THEN '世界知识产权组织'
    WHEN 'PCT' THEN '专利合作条约入口'
    ELSE name_cn
  END,
  name_en = CASE internal_code
    WHEN 'EP' THEN 'European Patent Office'
    WHEN 'EM' THEN 'European Union Intellectual Property Office'
    WHEN 'WO' THEN 'World Intellectual Property Organization'
    WHEN 'PCT' THEN 'Patent Cooperation Treaty'
    ELSE name_en
  END,
  jurisdiction_type = CASE internal_code
    WHEN 'EP' THEN 'regional_office'
    WHEN 'EM' THEN 'regional_office'
    WHEN 'WO' THEN 'international_organization'
    WHEN 'PCT' THEN 'treaty_entry'
    ELSE jurisdiction_type
  END,
  wipo_st3_code = CASE internal_code
    WHEN 'EP' THEN 'EP'
    WHEN 'EM' THEN 'EM'
    WHEN 'WO' THEN 'WO'
    ELSE wipo_st3_code
  END
WHERE internal_code IN ('EP', 'EM', 'WO', 'PCT');

UPDATE fee_rules t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE country_path_rules t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE entity_type_rules t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE language_rules t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE fx_tax_rules t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE special_rules t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE quotation_draft_items t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE quotations t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;
UPDATE quotation_items t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.country_code IS NOT NULL AND t.jurisdiction_id IS NULL;
UPDATE quotation_openings t JOIN country_jurisdiction_map m ON m.country_code = t.country_code SET t.jurisdiction_id = m.jurisdiction_id WHERE t.jurisdiction_id IS NULL;

CALL add_index_if_missing('countries', 'idx_countries_jurisdiction_id', 'KEY `idx_countries_jurisdiction_id` (`jurisdiction_id`)');
CALL add_index_if_missing('fee_rules', 'idx_fee_rules_jurisdiction_match', 'KEY `idx_fee_rules_jurisdiction_match` (`jurisdiction_id`, `application_type`, `filing_route`, `is_active`, `is_default`)');
CALL add_index_if_missing('country_path_rules', 'idx_country_path_rules_jurisdiction', 'KEY `idx_country_path_rules_jurisdiction` (`jurisdiction_id`, `application_type`, `filing_route`, `enabled`)');
CALL add_index_if_missing('entity_type_rules', 'idx_entity_type_rules_jurisdiction', 'KEY `idx_entity_type_rules_jurisdiction` (`jurisdiction_id`, `application_type`, `filing_route`, `enabled`)');
CALL add_index_if_missing('language_rules', 'idx_language_rules_jurisdiction', 'KEY `idx_language_rules_jurisdiction` (`jurisdiction_id`, `application_type`, `enabled`)');
CALL add_index_if_missing('fx_tax_rules', 'idx_fx_tax_rules_jurisdiction', 'KEY `idx_fx_tax_rules_jurisdiction` (`jurisdiction_id`, `quote_currency`, `enabled`)');
CALL add_index_if_missing('special_rules', 'idx_special_rules_jurisdiction', 'KEY `idx_special_rules_jurisdiction` (`jurisdiction_id`, `application_type`, `filing_route`, `enabled`)');
CALL add_index_if_missing('quotation_draft_items', 'idx_qdi_jurisdiction', 'KEY `idx_qdi_jurisdiction` (`jurisdiction_id`, `application_type`, `filing_route`)');
CALL add_index_if_missing('quotations', 'idx_quotations_jurisdiction', 'KEY `idx_quotations_jurisdiction` (`jurisdiction_id`)');
CALL add_index_if_missing('quotation_items', 'idx_qi_jurisdiction_opening', 'KEY `idx_qi_jurisdiction_opening` (`jurisdiction_id`, `application_type`, `filing_route`, `opening_status`)');
CALL add_index_if_missing('quotation_openings', 'idx_openings_jurisdiction_stats', 'KEY `idx_openings_jurisdiction_stats` (`jurisdiction_id`, `application_type`, `opened_at`)');

CALL add_fk_if_missing('countries', 'fk_countries_jurisdiction', 'fk_countries_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('fee_rules', 'fk_fee_rules_jurisdiction', 'fk_fee_rules_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('country_path_rules', 'fk_cpr_jurisdiction', 'fk_cpr_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('entity_type_rules', 'fk_etr_jurisdiction', 'fk_etr_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('language_rules', 'fk_language_rules_jurisdiction', 'fk_language_rules_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('fx_tax_rules', 'fk_fx_tax_rules_jurisdiction', 'fk_fx_tax_rules_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('special_rules', 'fk_special_rules_jurisdiction', 'fk_special_rules_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('quotation_draft_items', 'fk_qdi_jurisdiction', 'fk_qdi_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('quotations', 'fk_quotations_jurisdiction', 'fk_quotations_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('quotation_items', 'fk_qi_jurisdiction', 'fk_qi_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');
CALL add_fk_if_missing('quotation_openings', 'fk_openings_jurisdiction', 'fk_openings_jurisdiction FOREIGN KEY (`jurisdiction_id`) REFERENCES `jurisdictions`(`jurisdiction_id`)');

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
DROP PROCEDURE IF EXISTS add_fk_if_missing;
