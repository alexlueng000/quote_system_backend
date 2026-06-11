USE quote_system;
SET NAMES utf8mb4;

ALTER DATABASE quote_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- The affected data was inserted as UTF-8 text through a latin1 client, so
-- values are mojibake such as "å®˜è´¹" stored in utf8mb4 columns. Normalize the
-- column metadata first, then decode only values whose latin1 reinterpretation
-- produces CJK text. This keeps already-correct Chinese and plain English
-- values untouched.

ALTER TABLE users
  MODIFY name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
UPDATE users
SET name = CONVERT(CAST(CONVERT(name USING latin1) AS BINARY) USING utf8mb4)
WHERE name NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(name USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE countries
  MODIFY name_cn VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY name_en VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY application_language VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY application_cycle VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY country_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '单一国家',
  MODIFY international_region VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY business_region VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY region_remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE countries
SET name_cn = CONVERT(CAST(CONVERT(name_cn USING latin1) AS BINARY) USING utf8mb4)
WHERE name_cn NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(name_cn USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET name_en = CONVERT(CAST(CONVERT(name_en USING latin1) AS BINARY) USING utf8mb4)
WHERE name_en NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(name_en USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET application_language = CONVERT(CAST(CONVERT(application_language USING latin1) AS BINARY) USING utf8mb4)
WHERE application_language NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_language USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET application_cycle = CONVERT(CAST(CONVERT(application_cycle USING latin1) AS BINARY) USING utf8mb4)
WHERE application_cycle NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_cycle USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET country_type = CONVERT(CAST(CONVERT(country_type USING latin1) AS BINARY) USING utf8mb4)
WHERE country_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(country_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET international_region = CONVERT(CAST(CONVERT(international_region USING latin1) AS BINARY) USING utf8mb4)
WHERE international_region NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(international_region USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET business_region = CONVERT(CAST(CONVERT(business_region USING latin1) AS BINARY) USING utf8mb4)
WHERE business_region NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(business_region USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE countries
SET region_remark = CONVERT(CAST(CONVERT(region_remark USING latin1) AS BINARY) USING utf8mb4)
WHERE region_remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(region_remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE fee_rule_versions
  MODIFY version_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE fee_rule_versions
SET version_name = CONVERT(CAST(CONVERT(version_name USING latin1) AS BINARY) USING utf8mb4)
WHERE version_name NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(version_name USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rule_versions
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE fee_rules
  MODIFY application_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY filing_route VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY pct_route_detail VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY entity_type VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY stage VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY item_group_key VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY item_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY fee_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY fee_category VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '其他',
  MODIFY trigger_condition VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY cost_nature VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE fee_rules
SET application_type = CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4)
WHERE application_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET filing_route = CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4)
WHERE filing_route NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET pct_route_detail = CONVERT(CAST(CONVERT(pct_route_detail USING latin1) AS BINARY) USING utf8mb4)
WHERE pct_route_detail NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(pct_route_detail USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET entity_type = CONVERT(CAST(CONVERT(entity_type USING latin1) AS BINARY) USING utf8mb4)
WHERE entity_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(entity_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET stage = CONVERT(CAST(CONVERT(stage USING latin1) AS BINARY) USING utf8mb4)
WHERE stage NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(stage USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET item_group_key = CONVERT(CAST(CONVERT(item_group_key USING latin1) AS BINARY) USING utf8mb4)
WHERE item_group_key NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(item_group_key USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET item_name = CONVERT(CAST(CONVERT(item_name USING latin1) AS BINARY) USING utf8mb4)
WHERE item_name NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(item_name USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET fee_type = CONVERT(CAST(CONVERT(fee_type USING latin1) AS BINARY) USING utf8mb4)
WHERE fee_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(fee_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET fee_category = CONVERT(CAST(CONVERT(fee_category USING latin1) AS BINARY) USING utf8mb4)
WHERE fee_category NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(fee_category USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET trigger_condition = CONVERT(CAST(CONVERT(trigger_condition USING latin1) AS BINARY) USING utf8mb4)
WHERE trigger_condition NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(trigger_condition USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET cost_nature = CONVERT(CAST(CONVERT(cost_nature USING latin1) AS BINARY) USING utf8mb4)
WHERE cost_nature NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(cost_nature USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fee_rules
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
ALTER TABLE fee_rules
  MODIFY fee_category ENUM(
    '官费',
    '官费对应外所合作所服务费',
    '官费对应本所服务费',
    '第三方代垫费',
    '第三方代垫对应合作所服务费',
    '第三方代垫对应本所服务费',
    '外所费',
    '本所费',
    '翻译费',
    '其他'
  ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '其他',
  MODIFY cost_nature ENUM('当前费用', '后续预估') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

ALTER TABLE translation_schemes
  MODIFY scheme_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
UPDATE translation_schemes
SET scheme_name = CONVERT(CAST(CONVERT(scheme_name USING latin1) AS BINARY) USING utf8mb4)
WHERE scheme_name NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(scheme_name USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE translation_rules
  MODIFY item_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY unit VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
UPDATE translation_rules
SET item_name = CONVERT(CAST(CONVERT(item_name USING latin1) AS BINARY) USING utf8mb4)
WHERE item_name NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(item_name USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE translation_rules
SET unit = CONVERT(CAST(CONVERT(unit USING latin1) AS BINARY) USING utf8mb4)
WHERE unit NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(unit USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE quotation_drafts
  MODIFY status ENUM('草稿', '已合并正式报价', '已作废')
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '草稿';

ALTER TABLE quotation_draft_items
  MODIFY status ENUM('草稿', '已选择', '已合并正式报价', '已删除')
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '草稿';

ALTER TABLE country_path_rules
  MODIFY application_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY filing_route VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY route_detail VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE country_path_rules
SET application_type = CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4)
WHERE application_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE country_path_rules
SET filing_route = CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4)
WHERE filing_route NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE country_path_rules
SET route_detail = CONVERT(CAST(CONVERT(route_detail USING latin1) AS BINARY) USING utf8mb4)
WHERE route_detail NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(route_detail USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE country_path_rules
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE entity_type_rules
  MODIFY application_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY filing_route VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE entity_type_rules
SET application_type = CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4)
WHERE application_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE entity_type_rules
SET filing_route = CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4)
WHERE filing_route NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE entity_type_rules
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE language_rules
  MODIFY application_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY source_language VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY target_language VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY intermediate_language VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE language_rules
SET application_type = CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4)
WHERE application_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE language_rules
SET source_language = CONVERT(CAST(CONVERT(source_language USING latin1) AS BINARY) USING utf8mb4)
WHERE source_language NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(source_language USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE language_rules
SET target_language = CONVERT(CAST(CONVERT(target_language USING latin1) AS BINARY) USING utf8mb4)
WHERE target_language NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(target_language USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE language_rules
SET intermediate_language = CONVERT(CAST(CONVERT(intermediate_language USING latin1) AS BINARY) USING utf8mb4)
WHERE intermediate_language NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(intermediate_language USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE language_rules
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE fx_tax_rules
  MODIFY version VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE fx_tax_rules
SET version = CONVERT(CAST(CONVERT(version USING latin1) AS BINARY) USING utf8mb4)
WHERE version NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(version USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE fx_tax_rules
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';

ALTER TABLE special_rules
  MODIFY application_type VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY filing_route VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY rule_type VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  MODIFY risk_summary VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY linked_rule_code VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  MODIFY remark VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';
UPDATE special_rules
SET application_type = CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4)
WHERE application_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(application_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE special_rules
SET filing_route = CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4)
WHERE filing_route NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(filing_route USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE special_rules
SET rule_type = CONVERT(CAST(CONVERT(rule_type USING latin1) AS BINARY) USING utf8mb4)
WHERE rule_type NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(rule_type USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE special_rules
SET risk_summary = CONVERT(CAST(CONVERT(risk_summary USING latin1) AS BINARY) USING utf8mb4)
WHERE risk_summary NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(risk_summary USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE special_rules
SET linked_rule_code = CONVERT(CAST(CONVERT(linked_rule_code USING latin1) AS BINARY) USING utf8mb4)
WHERE linked_rule_code NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(linked_rule_code USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
UPDATE special_rules
SET remark = CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4)
WHERE remark NOT REGEXP '[一-龥]'
  AND CONVERT(CAST(CONVERT(remark USING latin1) AS BINARY) USING utf8mb4) REGEXP '[一-龥]';
