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

CALL add_column_if_missing('jurisdictions', 'quote_selectable', '`quote_selectable` TINYINT(1) NOT NULL DEFAULT 0 AFTER `is_enabled`');
CALL add_column_if_missing('jurisdictions', 'quote_business_lines_json', '`quote_business_lines_json` JSON NULL AFTER `quote_selectable`');
CALL add_column_if_missing('jurisdictions', 'quote_option_group', '`quote_option_group` VARCHAR(50) NOT NULL DEFAULT '''' AFTER `quote_business_lines_json`');
CALL add_column_if_missing('jurisdictions', 'quote_display_name', '`quote_display_name` VARCHAR(180) NOT NULL DEFAULT '''' AFTER `quote_option_group`');
CALL add_column_if_missing('jurisdictions', 'not_selectable_reason', '`not_selectable_reason` VARCHAR(255) NULL AFTER `quote_display_name`');

INSERT INTO jurisdictions (
  jurisdiction_id, internal_code, display_code, name_cn, name_en,
  jurisdiction_type, is_enabled, display_order, wipo_st3_code,
  source_name, source_url, source_version, last_verified_at,
  source_verified, source_verified_at, source_verified_by,
  manual_override, remarks,
  quote_selectable, quote_business_lines_json, quote_option_group,
  quote_display_name, not_selectable_reason
)
VALUES
  (
    'jur-WO', 'WO', 'WIPO', '世界知识产权组织', 'World Intellectual Property Organization',
    'international_organization', 1, 900, 'WO',
    'WIPO ST.3 / WIPO official website', 'https://www.wipo.int/',
    'WIPO ST.3 December 2025; WIPO current official website', NOW(),
    1, NOW(), 'phase_3_quote_jurisdiction_preview',
    0, 'Phase 3 quote preview object; not mapped to legacy countries.',
    1, JSON_ARRAY('patent'), 'international_organization',
    '世界知识产权组织 / WIPO', NULL
  ),
  (
    'jur-PCT', 'PCT', 'PCT', '专利合作条约入口', 'Patent Cooperation Treaty',
    'treaty_entry', 1, 910, NULL,
    'WIPO PCT', 'https://www.wipo.int/pct/en/',
    'WIPO PCT current official page', NOW(),
    1, NOW(), 'phase_3_quote_jurisdiction_preview',
    0, 'Phase 3 quote preview treaty route object; not mapped to legacy countries.',
    0, JSON_ARRAY('patent'), 'treaty_route',
    'PCT 国际阶段', 'PCT 国际阶段报价入口，待申请路径模块启用'
  ),
  (
    'jur-MADRID', 'MADRID', 'MADRID', '马德里商标国际注册入口', 'Madrid System',
    'treaty_entry', 1, 920, NULL,
    'WIPO Madrid System', 'https://www.wipo.int/madrid/en/',
    'WIPO Madrid current official page', NOW(),
    1, NOW(), 'phase_3_quote_jurisdiction_preview',
    0, 'Phase 3 quote preview treaty route object; not mapped to legacy countries.',
    0, JSON_ARRAY('trademark'), 'treaty_route',
    '马德里商标国际注册', '商标国际注册路径入口，待申请路径模块启用'
  ),
  (
    'jur-HAGUE', 'HAGUE', 'HAGUE', '海牙外观设计国际注册入口', 'Hague System',
    'treaty_entry', 1, 930, NULL,
    'WIPO Hague System', 'https://www.wipo.int/hague/en/',
    'WIPO Hague current official page', NOW(),
    1, NOW(), 'phase_3_quote_jurisdiction_preview',
    0, 'Phase 3 quote preview treaty route object; not mapped to legacy countries.',
    0, JSON_ARRAY('design'), 'treaty_route',
    '海牙外观设计国际注册', '外观设计国际注册路径入口，待申请路径模块启用'
  )
ON DUPLICATE KEY UPDATE
  name_cn = VALUES(name_cn),
  name_en = VALUES(name_en),
  jurisdiction_type = VALUES(jurisdiction_type),
  is_enabled = VALUES(is_enabled),
  source_name = VALUES(source_name),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  source_verified = VALUES(source_verified),
  source_verified_at = VALUES(source_verified_at),
  source_verified_by = VALUES(source_verified_by),
  quote_selectable = VALUES(quote_selectable),
  quote_business_lines_json = VALUES(quote_business_lines_json),
  quote_option_group = VALUES(quote_option_group),
  quote_display_name = VALUES(quote_display_name),
  not_selectable_reason = VALUES(not_selectable_reason);

UPDATE jurisdictions
SET quote_selectable = 1,
    quote_business_lines_json = JSON_ARRAY('patent', 'trademark', 'design'),
    quote_option_group = 'single_country',
    quote_display_name = CONCAT(name_cn, ' (', display_code, ')'),
    not_selectable_reason = NULL
WHERE jurisdiction_type = 'single_country';

UPDATE jurisdictions
SET quote_selectable = 1,
    quote_business_lines_json = JSON_ARRAY('patent'),
    quote_option_group = 'regional_office',
    quote_display_name = '欧洲专利局 (EPO)',
    not_selectable_reason = NULL
WHERE UPPER(internal_code) = 'EP' OR UPPER(display_code) = 'EPO';

UPDATE jurisdictions
SET quote_selectable = 1,
    quote_business_lines_json = JSON_ARRAY('trademark', 'design'),
    quote_option_group = 'regional_office',
    quote_display_name = '欧盟知识产权局 (EUIPO)',
    not_selectable_reason = NULL
WHERE UPPER(internal_code) = 'EM' OR UPPER(display_code) = 'EUIPO';

UPDATE jurisdictions
SET quote_selectable = 1,
    quote_business_lines_json = JSON_ARRAY('patent'),
    quote_option_group = 'international_organization',
    quote_display_name = '世界知识产权组织 / WIPO',
    not_selectable_reason = NULL
WHERE UPPER(internal_code) = 'WO' OR UPPER(display_code) = 'WIPO';

UPDATE jurisdictions
SET quote_selectable = 0,
    quote_business_lines_json = JSON_ARRAY('patent'),
    quote_option_group = 'treaty_route',
    quote_display_name = 'PCT 国际阶段',
    not_selectable_reason = 'PCT 国际阶段报价入口，待申请路径模块启用'
WHERE UPPER(internal_code) = 'PCT' OR UPPER(display_code) = 'PCT';

UPDATE jurisdictions
SET quote_selectable = 0,
    quote_business_lines_json = JSON_ARRAY('trademark'),
    quote_option_group = 'treaty_route',
    quote_display_name = '马德里商标国际注册',
    not_selectable_reason = '商标国际注册路径入口，待申请路径模块启用'
WHERE UPPER(internal_code) = 'MADRID' OR UPPER(display_code) = 'MADRID';

UPDATE jurisdictions
SET quote_selectable = 0,
    quote_business_lines_json = JSON_ARRAY('design'),
    quote_option_group = 'treaty_route',
    quote_display_name = '海牙外观设计国际注册',
    not_selectable_reason = '外观设计国际注册路径入口，待申请路径模块启用'
WHERE UPPER(internal_code) = 'HAGUE' OR UPPER(display_code) = 'HAGUE';

UPDATE jurisdictions
SET quote_selectable = 0,
    quote_business_lines_json = JSON_ARRAY(),
    quote_option_group = 'non_quote_region',
    quote_display_name = CASE
      WHEN quote_display_name = '' THEN CONCAT(name_cn, ' (', display_code, ')')
      ELSE quote_display_name
    END,
    not_selectable_reason = '欧洲仅作为地理区域或商务/经济区域，不作为报价对象'
WHERE UPPER(internal_code) IN ('EUROPE', 'EUR')
   OR UPPER(display_code) IN ('EUROPE', 'EUR')
   OR name_cn = '欧洲'
   OR LOWER(name_en) = 'europe';

UPDATE jurisdictions
SET quote_option_group = CASE
      WHEN jurisdiction_type = 'regional_office' THEN 'regional_office'
      WHEN jurisdiction_type = 'treaty_entry' THEN 'treaty_route'
      WHEN jurisdiction_type = 'international_organization' THEN 'international_organization'
      ELSE jurisdiction_type
    END,
    quote_display_name = CASE
      WHEN quote_display_name = '' THEN CONCAT(name_cn, ' (', display_code, ')')
      ELSE quote_display_name
    END,
    quote_business_lines_json = CASE
      WHEN quote_business_lines_json IS NULL THEN JSON_ARRAY()
      ELSE quote_business_lines_json
    END
WHERE quote_option_group = '' OR quote_display_name = '' OR quote_business_lines_json IS NULL;

CALL add_index_if_missing(
  'jurisdictions',
  'idx_jurisdictions_quote_preview',
  'KEY `idx_jurisdictions_quote_preview` (`quote_selectable`, `is_enabled`, `quote_option_group`, `display_order`, `internal_code`)'
);

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
