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

-- default_office_jurisdiction_id is a nullable logical link to another
-- jurisdictions row in this phase. Once office master coverage is complete,
-- it can be normalized into an enforced FK without changing the UI contract.
CALL add_column_if_missing('jurisdictions', 'default_office_jurisdiction_id', '`default_office_jurisdiction_id` VARCHAR(64) NULL AFTER `not_selectable_reason`');
CALL add_column_if_missing('jurisdictions', 'default_office_code', '`default_office_code` VARCHAR(50) NOT NULL DEFAULT '''' AFTER `default_office_jurisdiction_id`');
CALL add_column_if_missing('jurisdictions', 'default_office_name_cn', '`default_office_name_cn` VARCHAR(180) NOT NULL DEFAULT '''' AFTER `default_office_code`');
CALL add_column_if_missing('jurisdictions', 'default_office_name_en', '`default_office_name_en` VARCHAR(220) NOT NULL DEFAULT '''' AFTER `default_office_name_cn`');
CALL add_column_if_missing('jurisdictions', 'default_office_type', '`default_office_type` VARCHAR(80) NOT NULL DEFAULT '''' AFTER `default_office_name_en`');
CALL add_column_if_missing('jurisdictions', 'default_office_source_note', '`default_office_source_note` VARCHAR(800) NOT NULL DEFAULT '''' AFTER `default_office_type`');
CALL add_index_if_missing('jurisdictions', 'idx_jurisdictions_default_office', 'KEY `idx_jurisdictions_default_office` (`default_office_jurisdiction_id`, `default_office_code`)');

INSERT INTO jurisdiction_data_source_registry (
  source_id, source_name, source_type, source_owner, source_url,
  source_version, applicable_fields_json, verification_frequency, source_note,
  source_verified, review_status, is_active
)
VALUES (
  'WIPO_IP_OFFICES_DIRECTORY',
  'WIPO Country Profiles - Directory of IP Offices',
  'official',
  'WIPO',
  'https://www.wipo.int/en/web/country-profiles/directory-ip-offices',
  'Current WIPO online directory',
  JSON_ARRAY('default_office_code', 'default_office_name_cn', 'default_office_name_en', 'default_office_type'),
  'annual_or_before_office_master_patch',
  '主管局/受理局来源优先使用 WIPO Country Profiles - Directory of IP Offices；缩写不明确时允许人工维护并标记 pending_review 或 manual_verified。',
  0,
  'pending_review',
  1
)
ON DUPLICATE KEY UPDATE
  source_name = VALUES(source_name),
  source_type = VALUES(source_type),
  source_owner = VALUES(source_owner),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  applicable_fields_json = VALUES(applicable_fields_json),
  verification_frequency = VALUES(verification_frequency),
  source_note = VALUES(source_note),
  review_status = VALUES(review_status),
  is_active = VALUES(is_active);

INSERT INTO jurisdiction_data_source_registry (
  source_id, source_name, source_type, source_owner, source_url,
  source_version, applicable_fields_json, verification_frequency, source_note,
  source_verified, review_status, is_active
)
VALUES (
  'UN_M49',
  'UNSD Standard Country or Area Codes for Statistical Use',
  'official',
  'United Nations Statistics Division',
  'https://unstats.un.org/unsd/methodology/m49/',
  'Current online table',
  JSON_ARRAY('international_region', 'un_m49_code'),
  'semi_annual_or_on_major_change',
  '地理区域/次区域口径使用 UN M49；不替代 WIPO ST.3 作为本系统专利业务国家/地区标准代码。',
  0,
  'pending_review',
  1
)
ON DUPLICATE KEY UPDATE
  source_name = VALUES(source_name),
  source_type = VALUES(source_type),
  source_owner = VALUES(source_owner),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  applicable_fields_json = VALUES(applicable_fields_json),
  verification_frequency = VALUES(verification_frequency),
  source_note = VALUES(source_note),
  review_status = VALUES(review_status),
  is_active = VALUES(is_active);

INSERT INTO jurisdiction_data_source_registry (
  source_id, source_name, source_type, source_owner, source_url,
  source_version, applicable_fields_json, verification_frequency, source_note,
  source_verified, review_status, is_active
)
VALUES (
  'BUSINESS_REGION_SOURCE',
  'Internal business and market tag source',
  'internal',
  'internal',
  'internal://business-region-tags',
  'internal tag policy 2026-06',
  JSON_ARRAY('business_region', 'default_business_economic_regions'),
  'semi_annual_or_policy_change',
  '商务/市场标签来源；空值表示未配置，不强制回填 OTHER；拉美为商务标签，南美不作为同级商务标签。',
  0,
  'pending_review',
  1
)
ON DUPLICATE KEY UPDATE
  source_name = VALUES(source_name),
  source_type = VALUES(source_type),
  source_owner = VALUES(source_owner),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  applicable_fields_json = VALUES(applicable_fields_json),
  verification_frequency = VALUES(verification_frequency),
  source_note = VALUES(source_note),
  review_status = VALUES(review_status),
  is_active = VALUES(is_active);

INSERT INTO jurisdiction_reference_registry (
  reference_id, standard_code, display_code, name_cn, name_en, aliases_json,
  jurisdiction_type, reference_category, business_scope_json, visibility_scope,
  candidate_status, quote_selectable_default, not_selectable_reason, reserved_reason,
  geo_region, default_business_economic_regions_json, source_id, source_name,
  source_url, source_version, source_note, source_verified, review_status,
  is_active, default_currency_legacy
)
VALUES (
  'ref-co', 'CO', 'CO', '哥伦比亚', 'Colombia',
  JSON_ARRAY('CO', 'COL', 'Colombia', '哥伦比亚'),
  'single_country', 'country', JSON_ARRAY('patent', 'design'), 'country_master_reference',
  'candidate', 0, '未纳入当前报价范围', '',
  'Latin America and the Caribbean', JSON_ARRAY('LATIN_AMERICA'),
  'WIPO_ST3', 'WIPO ST.3 / UN M49',
  'https://www.wipo.int/standards/en/part_03_standards.html',
  'WIPO ST.3 current; UN M49 current',
  'Colombia = CO 以 WIPO ST.3 作为专利业务标准代码；地理区域以 UN M49 拉丁美洲和加勒比口径复核。',
  0, 'pending_review', 1, 'COP'
)
ON DUPLICATE KEY UPDATE
  display_code = VALUES(display_code),
  aliases_json = VALUES(aliases_json),
  geo_region = VALUES(geo_region),
  default_business_economic_regions_json = VALUES(default_business_economic_regions_json),
  source_id = VALUES(source_id),
  source_name = VALUES(source_name),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  source_note = VALUES(source_note),
  review_status = VALUES(review_status),
  is_active = VALUES(is_active);

UPDATE jurisdiction_reference_registry
SET geo_region = 'Europe',
    default_business_economic_regions_json = JSON_ARRAY(),
    source_id = CASE WHEN source_id = 'WIPO_LEX_REFERENCE' THEN 'WIPO_ST3' ELSE source_id END,
    source_name = CASE WHEN source_name LIKE '%WIPO Lex%' THEN 'WIPO ST.3 / UN M49 field baseline' ELSE source_name END,
    source_url = CASE WHEN source_url LIKE '%wipolex%' THEN 'https://www.wipo.int/standards/en/part_03_standards.html; https://unstats.un.org/unsd/methodology/m49/' ELSE source_url END,
    source_version = CASE WHEN source_version = '' OR source_version LIKE '%WIPO Lex%' THEN 'WIPO ST.3 current; UN M49 current' ELSE source_version END,
    source_note = 'Switzerland standard_code=CH uses WIPO ST.3; international_region uses UN M49 Europe; WIPO Lex is only a candidate pool supplement.'
WHERE reference_id = 'ref-ch'
  AND jurisdiction_id IS NULL;

UPDATE countries
SET international_region = 'Latin America and the Caribbean',
    business_region = CASE
      WHEN business_region IS NULL OR business_region = '' OR business_region = 'Other'
        OR business_region = '["OTHER"]' OR business_region LIKE '%OTHER%' OR business_region LIKE '%SOUTH_AMERICA%'
      THEN JSON_ARRAY('LATIN_AMERICA')
      ELSE business_region
    END
WHERE UPPER(code) = 'CO';

UPDATE jurisdictions
SET un_m49_code = COALESCE(NULLIF(un_m49_code, ''), '170'),
    wipo_st3_code = 'CO',
    source_name = CASE WHEN source_name = '' THEN 'WIPO ST.3 / UN M49 / WIPO IP Offices Directory' ELSE source_name END,
    source_url = CASE WHEN source_url = '' THEN 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices' ELSE source_url END,
    source_version = CASE WHEN source_version = '' THEN 'WIPO ST.3 current; UN M49 current; WIPO IP Offices Directory current' ELSE source_version END,
    default_office_code = CASE WHEN default_office_code = '' THEN 'SIC' ELSE default_office_code END,
    default_office_name_cn = CASE WHEN default_office_name_cn = '' THEN '哥伦比亚工业和商业监督局' ELSE default_office_name_cn END,
    default_office_name_en = CASE WHEN default_office_name_en = '' THEN 'Superintendence of Industry and Commerce' ELSE default_office_name_en END,
    default_office_type = CASE WHEN default_office_type = '' THEN 'national_ip_office' ELSE default_office_type END,
    default_office_source_note = CASE WHEN default_office_source_note = '' THEN '主管局来源：WIPO Country Profiles - Directory of IP Offices；office display code 人工复核。' ELSE default_office_source_note END
WHERE UPPER(internal_code) = 'CO'
   OR UPPER(display_code) = 'CO'
   OR UPPER(wipo_st3_code) = 'CO';

UPDATE jurisdictions j
LEFT JOIN jurisdictions office_j ON office_j.internal_code = 'EP' OR office_j.display_code = 'EPO'
SET j.default_office_jurisdiction_id = COALESCE(j.default_office_jurisdiction_id, office_j.jurisdiction_id),
    j.default_office_code = CASE WHEN j.default_office_code = '' THEN 'EPO' ELSE j.default_office_code END,
    j.default_office_name_cn = CASE WHEN j.default_office_name_cn = '' THEN '欧洲专利局' ELSE j.default_office_name_cn END,
    j.default_office_name_en = CASE WHEN j.default_office_name_en = '' THEN 'European Patent Office' ELSE j.default_office_name_en END,
    j.default_office_type = CASE WHEN j.default_office_type = '' THEN 'regional_office' ELSE j.default_office_type END,
    j.default_office_source_note = CASE WHEN j.default_office_source_note = '' THEN '主管局对象优先关联同一主档 EPO；来源参考 WIPO IP Offices Directory / EPO official source。' ELSE j.default_office_source_note END
WHERE UPPER(j.internal_code) = 'EP' OR UPPER(j.display_code) = 'EPO';

UPDATE jurisdictions j
LEFT JOIN jurisdictions office_j ON office_j.internal_code = 'EM' OR office_j.display_code = 'EUIPO'
SET j.default_office_jurisdiction_id = COALESCE(j.default_office_jurisdiction_id, office_j.jurisdiction_id),
    j.default_office_code = CASE WHEN j.default_office_code = '' THEN 'EUIPO' ELSE j.default_office_code END,
    j.default_office_name_cn = CASE WHEN j.default_office_name_cn = '' THEN '欧盟知识产权局' ELSE j.default_office_name_cn END,
    j.default_office_name_en = CASE WHEN j.default_office_name_en = '' THEN 'European Union Intellectual Property Office' ELSE j.default_office_name_en END,
    j.default_office_type = CASE WHEN j.default_office_type = '' THEN 'regional_office' ELSE j.default_office_type END,
    j.default_office_source_note = CASE WHEN j.default_office_source_note = '' THEN '主管局对象优先关联同一主档 EUIPO；来源参考 WIPO IP Offices Directory / EUIPO official source。' ELSE j.default_office_source_note END
WHERE UPPER(j.internal_code) = 'EM' OR UPPER(j.display_code) = 'EUIPO';

UPDATE jurisdictions j
LEFT JOIN jurisdictions office_j ON office_j.internal_code = 'WO' OR office_j.display_code = 'WIPO'
SET j.default_office_jurisdiction_id = COALESCE(j.default_office_jurisdiction_id, office_j.jurisdiction_id),
    j.default_office_code = CASE WHEN j.default_office_code = '' THEN 'WIPO/IB' ELSE j.default_office_code END,
    j.default_office_name_cn = CASE WHEN j.default_office_name_cn = '' THEN '世界知识产权组织国际局' ELSE j.default_office_name_cn END,
    j.default_office_name_en = CASE WHEN j.default_office_name_en = '' THEN 'International Bureau of WIPO' ELSE j.default_office_name_en END,
    j.default_office_type = CASE WHEN j.default_office_type = '' THEN 'international_bureau' ELSE j.default_office_type END,
    j.default_office_source_note = CASE WHEN j.default_office_source_note = '' THEN 'WIPO/IB 作为国际局角色展示，候选搜索中 IB 不作为独立主档候选。' ELSE j.default_office_source_note END
WHERE UPPER(j.internal_code) = 'WO' OR UPPER(j.display_code) = 'WIPO';

UPDATE jurisdictions
SET default_office_code = CASE UPPER(internal_code)
      WHEN 'CN' THEN 'CNIPA'
      WHEN 'US' THEN 'USPTO'
      WHEN 'JP' THEN 'JPO'
      WHEN 'KR' THEN 'MOIP'
      WHEN 'DE' THEN 'DPMA'
      ELSE default_office_code
    END,
    default_office_name_cn = CASE UPPER(internal_code)
      WHEN 'CN' THEN '国家知识产权局'
      WHEN 'US' THEN '美国专利商标局'
      WHEN 'JP' THEN '日本特许厅'
      WHEN 'KR' THEN '韩国知识产权部'
      WHEN 'DE' THEN '德国专利商标局'
      ELSE default_office_name_cn
    END,
    default_office_name_en = CASE UPPER(internal_code)
      WHEN 'CN' THEN 'China National Intellectual Property Administration'
      WHEN 'US' THEN 'United States Patent and Trademark Office'
      WHEN 'JP' THEN 'Japan Patent Office'
      WHEN 'KR' THEN 'Ministry of Intellectual Property'
      WHEN 'DE' THEN 'German Patent and Trade Mark Office'
      ELSE default_office_name_en
    END,
    default_office_type = CASE
      WHEN UPPER(internal_code) IN ('CN', 'US', 'JP', 'KR', 'DE') AND default_office_type = '' THEN 'national_ip_office'
      ELSE default_office_type
    END,
    default_office_source_note = CASE
      WHEN UPPER(internal_code) = 'KR'
      THEN '主管局来源：WIPO Country Profiles - Directory of IP Offices；当前主管局为 Ministry of Intellectual Property (MOIP)，KIPO 仅作为历史名称/搜索别名。'
      WHEN UPPER(internal_code) IN ('CN', 'US', 'JP', 'KR', 'DE') AND default_office_source_note = ''
      THEN '主管局来源优先参考 WIPO Country Profiles - Directory of IP Offices；缩写按业务常用 office display code 维护。'
      ELSE default_office_source_note
    END
WHERE UPPER(internal_code) IN ('CN', 'US', 'JP', 'KR', 'DE');

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
