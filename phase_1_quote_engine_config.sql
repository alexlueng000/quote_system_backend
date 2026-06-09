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
    SET @alter_sql = CONCAT(
      'ALTER TABLE `',
      table_name_value,
      '` ADD COLUMN ',
      column_definition_value
    );
    PREPARE alter_statement FROM @alter_sql;
    EXECUTE alter_statement;
    DEALLOCATE PREPARE alter_statement;
  END IF;
END//
DELIMITER ;

CALL add_column_if_missing('countries', 'country_type', CONCAT('`country_type` VARCHAR(50) NOT NULL DEFAULT ', QUOTE('单一国家')));
CALL add_column_if_missing('countries', 'display_order', '`display_order` INT NOT NULL DEFAULT 0');
CALL add_column_if_missing('countries', 'international_region', CONCAT('`international_region` VARCHAR(100) NOT NULL DEFAULT ', QUOTE('')));
CALL add_column_if_missing('countries', 'business_region', CONCAT('`business_region` VARCHAR(500) NOT NULL DEFAULT ', QUOTE('')));
ALTER TABLE countries
  MODIFY business_region VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
CALL add_column_if_missing('countries', 'region_remark', CONCAT('`region_remark` VARCHAR(500) NOT NULL DEFAULT ', QUOTE('')));

DROP PROCEDURE IF EXISTS add_column_if_missing;

CREATE TABLE IF NOT EXISTS country_path_rules (
  id VARCHAR(64) PRIMARY KEY,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL,
  route_detail VARCHAR(100) NOT NULL DEFAULT '',
  affects_official_fee TINYINT(1) NOT NULL DEFAULT 0,
  affects_local_service_fee TINYINT(1) NOT NULL DEFAULT 0,
  affects_inhouse_service_fee TINYINT(1) NOT NULL DEFAULT 0,
  affects_questions TINYINT(1) NOT NULL DEFAULT 0,
  affects_documents TINYINT(1) NOT NULL DEFAULT 0,
  affects_deadlines TINYINT(1) NOT NULL DEFAULT 0,
  affects_translation TINYINT(1) NOT NULL DEFAULT 0,
  affects_display TINYINT(1) NOT NULL DEFAULT 0,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  effective_date DATE NULL,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_country_path_rules_match (country_code, application_type, filing_route, enabled),
  CONSTRAINT fk_country_path_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS entity_type_rules (
  id VARCHAR(64) PRIMARY KEY,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL DEFAULT '',
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  entity_types_json JSON NULL,
  affects_official_fee TINYINT(1) NOT NULL DEFAULT 0,
  affects_questions TINYINT(1) NOT NULL DEFAULT 0,
  requires_customer_confirmation TINYINT(1) NOT NULL DEFAULT 0,
  requires_supporting_documents TINYINT(1) NOT NULL DEFAULT 0,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_entity_type_rules_match (country_code, application_type, filing_route, enabled),
  CONSTRAINT fk_entity_type_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS language_rules (
  id VARCHAR(64) PRIMARY KEY,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  accepted_languages_json JSON NULL,
  source_language VARCHAR(50) NOT NULL DEFAULT '',
  target_language VARCHAR(50) NOT NULL DEFAULT '',
  intermediate_language VARCHAR(50) NOT NULL DEFAULT '',
  needs_second_translation TINYINT(1) NOT NULL DEFAULT 0,
  recommended_scheme_id VARCHAR(64) NOT NULL DEFAULT '',
  default_translation_fee TINYINT(1) NOT NULL DEFAULT 0,
  allow_scheme_switch TINYINT(1) NOT NULL DEFAULT 1,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_language_rules_match (country_code, application_type, enabled),
  CONSTRAINT fk_language_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fx_tax_rules (
  id VARCHAR(64) PRIMARY KEY,
  country_code VARCHAR(20) NOT NULL,
  official_currency VARCHAR(10) NOT NULL,
  official_quote_currency VARCHAR(10) NOT NULL,
  local_service_currency VARCHAR(10) NOT NULL,
  local_service_currency_options_json JSON NULL,
  quote_currency VARCHAR(10) NOT NULL,
  fx_rate DECIMAL(18, 6) NOT NULL DEFAULT 1.000000,
  tax_rate DECIMAL(8, 4) NOT NULL DEFAULT 0.0000,
  tax_included TINYINT(1) NOT NULL DEFAULT 0,
  lock_on_formal_quote TINYINT(1) NOT NULL DEFAULT 1,
  version VARCHAR(64) NOT NULL DEFAULT '',
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_fx_tax_rules_match (country_code, quote_currency, enabled),
  CONSTRAINT fk_fx_tax_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS special_rules (
  id VARCHAR(64) PRIMARY KEY,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL DEFAULT '',
  filing_route VARCHAR(50) NOT NULL DEFAULT '',
  rule_type VARCHAR(100) NOT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  triggers_extra_fee TINYINT(1) NOT NULL DEFAULT 0,
  triggers_risk_warning TINYINT(1) NOT NULL DEFAULT 0,
  requires_customer_confirmation TINYINT(1) NOT NULL DEFAULT 0,
  risk_summary VARCHAR(500) NOT NULL DEFAULT '',
  linked_rule_code VARCHAR(100) NOT NULL DEFAULT '',
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_special_rules_match (country_code, application_type, filing_route, enabled),
  CONSTRAINT fk_special_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_calculation_snapshots (
  id VARCHAR(64) PRIMARY KEY,
  quotation_id VARCHAR(36) NOT NULL,
  price_version_id VARCHAR(64) NULL,
  fx_tax_rule_id VARCHAR(64) NULL,
  quote_currency VARCHAR(10) NOT NULL,
  snapshot_json JSON NOT NULL,
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_calculation_snapshots_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

UPDATE countries
SET name_cn = CASE code
    WHEN 'EP' THEN '欧洲专利局'
    WHEN 'EM' THEN '欧盟知识产权局'
    WHEN 'WO' THEN '世界知识产权组织'
    WHEN 'PCT' THEN '专利合作条约入口'
    ELSE name_cn
  END,
  name_en = CASE code
    WHEN 'EP' THEN 'European Patent Office'
    WHEN 'EM' THEN 'European Union Intellectual Property Office'
    WHEN 'WO' THEN 'World Intellectual Property Organization'
    WHEN 'PCT' THEN 'Patent Cooperation Treaty'
    ELSE name_en
  END,
  country_type = CASE code
    WHEN 'EP' THEN '区域局'
    WHEN 'EM' THEN '区域局'
    WHEN 'WO' THEN '国际组织'
    WHEN 'PCT' THEN '条约体系入口'
    ELSE '单一国家'
  END,
  display_order = CASE code
    WHEN 'US' THEN 10
    WHEN 'EP' THEN 20
    WHEN 'JP' THEN 30
    WHEN 'KR' THEN 40
    WHEN 'EM' THEN 50
    WHEN 'WO' THEN 60
    WHEN 'PCT' THEN 70
    ELSE 100
  END,
  international_region = CASE code
    WHEN 'US' THEN 'North America'
    WHEN 'EP' THEN 'Europe'
    WHEN 'EM' THEN 'Europe'
    WHEN 'WO' THEN 'Other'
    WHEN 'PCT' THEN 'Other'
    WHEN 'JP' THEN 'Asia'
    WHEN 'KR' THEN 'Asia'
    ELSE international_region
  END,
  business_region = CASE code
    WHEN 'US' THEN '["NORTH_AMERICA","APEC"]'
    WHEN 'JP' THEN '["NORTHEAST_ASIA_JP_KR","APEC"]'
    WHEN 'KR' THEN '["NORTHEAST_ASIA_JP_KR","APEC"]'
    WHEN 'CN' THEN '["GREATER_CHINA","APEC"]'
    WHEN 'DE' THEN '["EUROPE","EU"]'
    WHEN 'EP' THEN '["EUROPE"]'
    WHEN 'EM' THEN '["EUROPE","EU"]'
    WHEN 'AU' THEN '["ANZ_OCEANIA","APEC"]'
    WHEN 'NZ' THEN '["ANZ_OCEANIA","APEC"]'
    WHEN 'SG' THEN '["SOUTHEAST_ASIA","ASEAN","APEC"]'
    WHEN 'WO' THEN '["OTHER"]'
    WHEN 'PCT' THEN '["OTHER"]'
    ELSE business_region
  END
WHERE code IN ('US', 'JP', 'KR', 'CN', 'DE', 'EP', 'EM', 'AU', 'NZ', 'SG', 'WO', 'PCT');

INSERT INTO country_path_rules (
  id, country_code, application_type, filing_route, route_detail,
  affects_official_fee, affects_local_service_fee, affects_inhouse_service_fee,
  affects_questions, affects_documents, affects_deadlines, affects_translation,
  affects_display, enabled, effective_date, remark
)
VALUES
  ('path-us-invention-pct-30', 'US', '发明', 'PCT进入', '30个月进入', 1, 1, 0, 1, 1, 1, 1, 1, 1, '2026-06-01', '美国 PCT 发明标准进入'),
  ('path-us-invention-pct-bypass', 'US', '发明', 'PCT进入', 'BYPASS', 1, 1, 0, 1, 1, 1, 1, 1, 1, '2026-06-01', '美国 BYPASS 预留细分'),
  ('path-ep-invention-pct-31', 'EP', '发明', 'PCT进入', '31个月进入', 1, 1, 0, 1, 1, 1, 1, 1, 1, '2026-06-01', 'EPO PCT 进入'),
  ('path-jp-invention-paris', 'JP', '发明', '巴黎公约', '', 1, 1, 0, 1, 1, 1, 1, 1, 1, '2026-06-01', '日本巴黎公约进入')
ON DUPLICATE KEY UPDATE
  route_detail = VALUES(route_detail),
  enabled = VALUES(enabled),
  remark = VALUES(remark);

INSERT INTO entity_type_rules (
  id, country_code, application_type, filing_route, enabled, entity_types_json,
  affects_official_fee, affects_questions, requires_customer_confirmation,
  requires_supporting_documents, remark
)
VALUES
  ('entity-us-invention-pct', 'US', '发明', 'PCT进入', 1, JSON_ARRAY('大实体', '小实体', '微实体'), 1, 1, 1, 1, '美国实体类型影响官费'),
  ('entity-ep-invention-pct', 'EP', '发明', 'PCT进入', 0, JSON_ARRAY(), 0, 0, 0, 0, 'EPO 暂不启用实体类型'),
  ('entity-jp-invention-paris', 'JP', '发明', '巴黎公约', 0, JSON_ARRAY(), 0, 0, 0, 0, '日本 V1 暂不启用实体类型')
ON DUPLICATE KEY UPDATE
  enabled = VALUES(enabled),
  entity_types_json = VALUES(entity_types_json),
  remark = VALUES(remark);

INSERT INTO language_rules (
  id, country_code, application_type, accepted_languages_json, source_language,
  target_language, intermediate_language, needs_second_translation,
  recommended_scheme_id, default_translation_fee, allow_scheme_switch, enabled, remark
)
VALUES
  ('lang-us-invention', 'US', '发明', JSON_ARRAY('英文'), '中文', '英文', '', 0, 'recommended-standard', 1, 1, 1, '中文稿进入美国默认带出翻译费'),
  ('lang-ep-invention', 'EP', '发明', JSON_ARRAY('英文', '法文', '德文'), '中文', '英文', '', 0, 'recommended-standard', 1, 1, 1, 'EPO 可接受英文/法文/德文'),
  ('lang-jp-invention', 'JP', '发明', JSON_ARRAY('日文'), '中文', '日文', '', 0, 'recommended-standard', 1, 1, 1, '日本默认目标语为日文')
ON DUPLICATE KEY UPDATE
  accepted_languages_json = VALUES(accepted_languages_json),
  target_language = VALUES(target_language),
  enabled = VALUES(enabled),
  remark = VALUES(remark);

INSERT INTO fx_tax_rules (
  id, country_code, official_currency, official_quote_currency,
  local_service_currency, local_service_currency_options_json, quote_currency,
  fx_rate, tax_rate, tax_included, lock_on_formal_quote, version, enabled, remark
)
VALUES
  ('fx-us-usd', 'US', 'USD', 'USD', 'USD', JSON_ARRAY('USD', 'CNY'), 'USD', 1.000000, 0.0000, 0, 1, 'FX-2026-06', 1, '美元报价'),
  ('fx-ep-eur', 'EP', 'EUR', 'EUR', 'EUR', JSON_ARRAY('EUR', 'CNY'), 'EUR', 1.000000, 0.0000, 0, 1, 'FX-2026-06', 1, '欧元报价'),
  ('fx-jp-jpy', 'JP', 'JPY', 'JPY', 'JPY', JSON_ARRAY('JPY', 'CNY'), 'JPY', 1.000000, 0.0000, 0, 1, 'FX-2026-06', 1, '日元报价')
ON DUPLICATE KEY UPDATE
  fx_rate = VALUES(fx_rate),
  tax_rate = VALUES(tax_rate),
  enabled = VALUES(enabled),
  remark = VALUES(remark);

INSERT INTO special_rules (
  id, country_code, application_type, filing_route, rule_type, enabled,
  triggers_extra_fee, triggers_risk_warning, requires_customer_confirmation,
  risk_summary, linked_rule_code, remark
)
VALUES
  ('special-us-late-doc', 'US', '发明', 'PCT进入', '后补文件', 1, 1, 1, 1, '后补文件可能产生额外程序费用。', 'US-LATE-DOC', 'V1 返回风险摘要'),
  ('special-ep-late-translation', 'EP', '发明', 'PCT进入', '后补翻译', 1, 1, 1, 1, '后补翻译需确认期限和附加费。', 'EP-LATE-TRANS', 'V1 返回风险摘要'),
  ('special-jp-priority', 'JP', '发明', '巴黎公约', '后补优先权文件', 1, 0, 1, 1, '优先权文件后补需确认官方期限。', 'JP-PRI-DOC', 'V1 返回风险摘要')
ON DUPLICATE KEY UPDATE
  enabled = VALUES(enabled),
  risk_summary = VALUES(risk_summary),
  remark = VALUES(remark);
