USE quote_system;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS jurisdiction_data_source_registry (
  source_id VARCHAR(80) PRIMARY KEY,
  source_name VARCHAR(200) NOT NULL,
  source_type VARCHAR(50) NOT NULL DEFAULT 'manual_verified',
  source_owner VARCHAR(150) NOT NULL DEFAULT '',
  source_url VARCHAR(800) NOT NULL DEFAULT '',
  source_version VARCHAR(180) NOT NULL DEFAULT '',
  applicable_fields_json JSON NULL,
  verification_frequency VARCHAR(80) NOT NULL DEFAULT '',
  source_note VARCHAR(1200) NOT NULL DEFAULT '',
  source_verified TINYINT(1) NOT NULL DEFAULT 0,
  source_verified_at DATETIME NULL,
  source_verified_by VARCHAR(255) NULL,
  last_reviewed_at DATETIME NULL,
  next_review_due_at DATETIME NULL,
  review_status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_jdsr_status_due (review_status, next_review_due_at),
  KEY idx_jdsr_active_type (is_active, source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS jurisdiction_reference_registry (
  reference_id VARCHAR(80) PRIMARY KEY,
  jurisdiction_id VARCHAR(64) NULL,
  standard_code VARCHAR(50) NOT NULL,
  display_code VARCHAR(50) NOT NULL,
  name_cn VARCHAR(120) NOT NULL,
  name_en VARCHAR(180) NOT NULL,
  aliases_json JSON NULL,
  jurisdiction_type VARCHAR(50) NOT NULL DEFAULT 'single_country',
  reference_category VARCHAR(50) NOT NULL DEFAULT 'country',
  business_scope_json JSON NULL,
  visibility_scope VARCHAR(50) NOT NULL DEFAULT 'country_master_reference',
  candidate_status VARCHAR(50) NOT NULL DEFAULT 'candidate',
  quote_selectable_default TINYINT(1) NOT NULL DEFAULT 0,
  not_selectable_reason VARCHAR(255) NOT NULL DEFAULT '未纳入当前报价范围',
  reserved_reason VARCHAR(120) NOT NULL DEFAULT '',
  geo_region VARCHAR(100) NOT NULL DEFAULT 'Other',
  default_business_economic_regions_json JSON NULL,
  source_id VARCHAR(80) NULL,
  source_name VARCHAR(200) NOT NULL DEFAULT '',
  source_url VARCHAR(800) NOT NULL DEFAULT '',
  source_version VARCHAR(180) NOT NULL DEFAULT '',
  source_note VARCHAR(1200) NOT NULL DEFAULT '',
  source_verified TINYINT(1) NOT NULL DEFAULT 0,
  source_verified_at DATETIME NULL,
  source_verified_by VARCHAR(255) NULL,
  last_reviewed_at DATETIME NULL,
  next_review_due_at DATETIME NULL,
  review_status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  default_currency_legacy VARCHAR(10) NOT NULL DEFAULT 'USD',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_jrr_standard_code (standard_code),
  KEY idx_jrr_display_code (display_code),
  KEY idx_jrr_jurisdiction (jurisdiction_id),
  KEY idx_jrr_visibility (visibility_scope, is_active, candidate_status),
  KEY idx_jrr_type_category (jurisdiction_type, reference_category),
  KEY idx_jrr_source (source_id),
  CONSTRAINT fk_jrr_jurisdiction
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id),
  CONSTRAINT fk_jrr_source
    FOREIGN KEY (source_id) REFERENCES jurisdiction_data_source_registry(source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS jurisdiction_region_tag_map (
  id VARCHAR(80) PRIMARY KEY,
  jurisdiction_id VARCHAR(64) NOT NULL,
  tag_scheme VARCHAR(80) NOT NULL,
  tag_code VARCHAR(80) NOT NULL,
  tag_name_cn VARCHAR(120) NOT NULL,
  tag_name_en VARCHAR(160) NOT NULL DEFAULT '',
  source_id VARCHAR(80) NULL,
  source_type VARCHAR(50) NOT NULL DEFAULT 'manual_verified',
  source_name VARCHAR(200) NOT NULL DEFAULT '',
  source_url VARCHAR(800) NOT NULL DEFAULT '',
  source_note VARCHAR(1200) NOT NULL DEFAULT '',
  source_verified TINYINT(1) NOT NULL DEFAULT 0,
  source_verified_at DATETIME NULL,
  source_verified_by VARCHAR(255) NULL,
  last_reviewed_at DATETIME NULL,
  next_review_due_at DATETIME NULL,
  review_status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
  effective_from DATE NULL,
  effective_to DATE NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  reason_note VARCHAR(800) NOT NULL DEFAULT '',
  created_by VARCHAR(255) NULL,
  updated_by VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_jrtm_tag (jurisdiction_id, tag_scheme, tag_code),
  KEY idx_jrtm_tag_lookup (tag_scheme, tag_code, is_active, review_status),
  KEY idx_jrtm_source (source_id),
  CONSTRAINT fk_jrtm_jurisdiction
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id),
  CONSTRAINT fk_jrtm_source
    FOREIGN KEY (source_id) REFERENCES jurisdiction_data_source_registry(source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO jurisdiction_data_source_registry (
  source_id, source_name, source_type, source_owner, source_url,
  source_version, applicable_fields_json, verification_frequency, source_note,
  source_verified, review_status, is_active
)
VALUES
  ('WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'official', 'WIPO',
   'https://www.wipo.int/wipolex/zh/members', 'P0 reference object baseline',
   JSON_ARRAY('standard_code', 'name_cn', 'name_en', 'reference_category'),
   'annual_or_before_reference_patch',
   '条约/组织查询侧 WIPO Lex reference 对象池；作为国家主档候选补全来源之一，不等于全量正式报价国家。',
   0, 'pending_review', 1),
  ('WIPO_ST3', 'WIPO Standard ST.3', 'official', 'WIPO',
   'https://www.wipo.int/standards/en/part_03_standards.html', 'WIPO ST.3 December 2025',
   JSON_ARRAY('standard_code', 'display_code', 'jurisdiction_type'),
   'annual_or_on_standard_update',
   '知识产权国家、实体和组织代码来源；用于区域局、国际组织等 IP 特有对象。',
   0, 'pending_review', 1),
  ('WIPO_TREATIES', 'WIPO Treaty Portals', 'official', 'WIPO',
   'https://www.wipo.int/treaties/en/', 'Current WIPO treaty pages',
   JSON_ARRAY('name_cn', 'name_en', 'jurisdiction_type', 'business_scope'),
   'annual_or_before_treaty_data_change',
   '用于 PCT、Hague、Madrid、Nice 等条约或体系入口的名称和业务范围核验。',
   0, 'pending_review', 1),
  ('BELT_AND_ROAD_SOURCE', '一带一路商务/市场标签来源待复核', 'manual_verified', 'internal',
   '', 'pending source confirmation',
   JSON_ARRAY('tag_scheme', 'tag_code', 'tag_name_cn', 'tag_name_en'),
   'semi_annual_or_policy_change',
   '一带一路仅作为商务/市场标签机制预留；本补丁不批量映射国家，待确认来源清单后再维护。',
   0, 'pending_review', 1)
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

UPDATE jurisdictions
SET jurisdiction_type = 'special_region',
    quote_option_group = CASE WHEN quote_option_group IN ('', 'single_country', 'country') THEN 'region' ELSE quote_option_group END,
    quote_display_name = CASE
      WHEN UPPER(internal_code) = 'HK' THEN '中国香港 (HK)'
      WHEN UPPER(internal_code) = 'MO' THEN '中国澳门 (MO)'
      WHEN UPPER(internal_code) = 'TW' THEN '中国台湾 (TW)'
      ELSE quote_display_name
    END
WHERE UPPER(internal_code) IN ('HK', 'MO', 'TW')
   OR UPPER(display_code) IN ('HK', 'MO', 'TW');

UPDATE countries
SET country_type = '特殊地区'
WHERE UPPER(code) IN ('HK', 'MO', 'TW');

INSERT INTO jurisdiction_reference_registry (
  reference_id, standard_code, display_code, name_cn, name_en, aliases_json,
  jurisdiction_type, reference_category, business_scope_json, visibility_scope,
  candidate_status, quote_selectable_default, not_selectable_reason, reserved_reason,
  geo_region, default_business_economic_regions_json, source_id, source_name,
  source_url, source_version, source_note, source_verified, review_status,
  is_active, default_currency_legacy
)
VALUES
  ('ref-cn', 'CN', 'CN', '中国', 'China', JSON_ARRAY('CN', 'CHN', '中国', 'China'),
   'single_country', 'country', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'Asia', JSON_ARRAY('GREATER_CHINA', 'APEC'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '最小闭环候选：来自现有 IP/WIPO reference 对象池；不等于正式报价国家。', 0, 'pending_review', 1, 'CNY'),
  ('ref-us', 'US', 'US', '美国', 'United States', JSON_ARRAY('US', 'USA', 'United States', 'United States of America', '美国'),
   'single_country', 'country', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'North America', JSON_ARRAY('NORTH_AMERICA', 'APEC'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '最小闭环候选：来自现有 IP/WIPO reference 对象池；不等于正式报价国家。', 0, 'pending_review', 1, 'USD'),
  ('ref-jp', 'JP', 'JP', '日本', 'Japan', JSON_ARRAY('JP', 'JPN', '日本', 'Japan'),
   'single_country', 'country', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'Asia', JSON_ARRAY('NORTHEAST_ASIA_JP_KR', 'APEC'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '最小闭环候选：来自现有 IP/WIPO reference 对象池；不等于正式报价国家。', 0, 'pending_review', 1, 'JPY'),
  ('ref-kr', 'KR', 'KR', '韩国', 'South Korea', JSON_ARRAY('KR', 'KOR', 'Republic of Korea', 'Korea', '韩国'),
   'single_country', 'country', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'Asia', JSON_ARRAY('NORTHEAST_ASIA_JP_KR', 'APEC'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '最小闭环候选：来自现有 IP/WIPO reference 对象池；不等于正式报价国家。', 0, 'pending_review', 1, 'KRW'),
  ('ref-hk', 'HK', 'HK', '中国香港', 'Hong Kong, China', JSON_ARRAY('HK', 'Hong Kong', 'Hong Kong, China', '香港', '中国香港'),
   'special_region', 'region', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'Asia', JSON_ARRAY('GREATER_CHINA', 'APEC'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '条约/组织查询侧已出现的 WIPO Lex reference 对象；不等于正式报价地区。', 0, 'pending_review', 1, 'HKD'),
  ('ref-mo', 'MO', 'MO', '中国澳门', 'Macao, China', JSON_ARRAY('MO', 'Macao', 'Macau', 'Macao, China', '澳门', '中国澳门'),
   'special_region', 'region', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'Asia', JSON_ARRAY('GREATER_CHINA'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '条约/组织查询侧已出现的 WIPO Lex reference 对象；不等于正式报价地区。', 0, 'pending_review', 1, 'MOP'),
  ('ref-tw', 'TW', 'TW', '中国台湾', 'Taiwan', JSON_ARRAY('TW', 'TWN', 'Taiwan', '中国台湾', '台湾'),
   'special_region', 'region', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '未纳入当前报价范围', '', 'Asia', JSON_ARRAY('GREATER_CHINA', 'APEC'),
   'WIPO_LEX_REFERENCE', 'WIPO Lex Members reference objects', 'https://www.wipo.int/wipolex/zh/members',
   'P0 reference object baseline', '条约/组织查询侧已出现的 WIPO Lex reference 对象；不等于正式报价地区。', 0, 'pending_review', 1, 'TWD'),
  ('ref-ep', 'EP', 'EPO', '欧洲专利局', 'European Patent Office', JSON_ARRAY('EP', 'EPO', 'European Patent Office', '欧洲专利局'),
   'regional_office', 'regional_office', JSON_ARRAY('patent'), 'country_master_reference',
   'candidate', 0, '区域局候选，不作为普通国家批量报价入口', '', 'Europe', JSON_ARRAY('EUROPE'),
   'WIPO_ST3', 'WIPO Standard ST.3', 'https://www.wipo.int/standards/en/part_03_standards.html',
   'WIPO ST.3 December 2025', '区域局 reference 候选；正式对象以 jurisdictions 为准。', 0, 'pending_review', 1, 'EUR'),
  ('ref-em', 'EM', 'EUIPO', '欧盟知识产权局', 'European Union Intellectual Property Office', JSON_ARRAY('EM', 'EUIPO', 'OHIM', '欧盟知识产权局'),
   'regional_office', 'regional_office', JSON_ARRAY('design'), 'country_master_reference',
   'candidate', 0, '区域局候选，不作为普通国家批量报价入口', '', 'Europe', JSON_ARRAY('EUROPE', 'EU'),
   'WIPO_ST3', 'WIPO Standard ST.3', 'https://www.wipo.int/standards/en/part_03_standards.html',
   'WIPO ST.3 December 2025', '区域局 reference 候选；正式对象以 jurisdictions 为准。', 0, 'pending_review', 1, 'EUR'),
  ('ref-wo', 'WO', 'WIPO', '世界知识产权组织', 'World Intellectual Property Organization', JSON_ARRAY('WO', 'WIPO', 'World Intellectual Property Organization', '世界知识产权组织'),
   'international_organization', 'international_organization', JSON_ARRAY('patent', 'design'), 'country_master_reference',
   'candidate', 0, '国际组织候选，不作为普通国家批量报价入口', '', 'Other', JSON_ARRAY('OTHER'),
   'WIPO_ST3', 'WIPO Standard ST.3', 'https://www.wipo.int/standards/en/part_03_standards.html',
   'WIPO ST.3 December 2025', '国际组织 reference 候选；正式对象以 jurisdictions 为准。', 0, 'pending_review', 1, 'CHF'),
  ('ref-pct', 'PCT', 'PCT', '专利合作条约入口', 'Patent Cooperation Treaty', JSON_ARRAY('PCT', 'Patent Cooperation Treaty', '专利合作条约'),
   'treaty_entry', 'treaty_route', JSON_ARRAY('patent'), 'country_master_reference',
   'reserved', 0, '条约路径入口预留，当前不作为报价台可选国家', 'treaty_route_reserved', 'Other', JSON_ARRAY('OTHER'),
   'WIPO_TREATIES', 'WIPO Treaty Portals', 'https://www.wipo.int/treaties/en/',
   'Current WIPO treaty pages', '条约入口 reference 候选；条约关系仍由 ip_system_master / relation 表承载。', 0, 'pending_review', 1, 'CHF'),
  ('ref-hague', 'HAGUE', 'HAGUE', '海牙体系入口', 'Hague System', JSON_ARRAY('HAGUE', 'Hague System', '海牙体系'),
   'treaty_entry', 'treaty_route', JSON_ARRAY('design'), 'country_master_reference',
   'reserved', 0, '外观设计国际注册路径预留，当前正式报价不启用', 'design_reserved', 'Other', JSON_ARRAY('OTHER'),
   'WIPO_TREATIES', 'WIPO Treaty Portals', 'https://www.wipo.int/treaties/en/',
   'Current WIPO treaty pages', '外观设计体系预留；本轮不启用正式报价。', 0, 'pending_review', 1, 'CHF'),
  ('ref-madrid', 'MADRID', 'MADRID', '马德里体系入口', 'Madrid System', JSON_ARRAY('MADRID', 'Madrid System', '马德里体系'),
   'treaty_entry', 'treaty_route', JSON_ARRAY('trademark'), 'reserved_hidden',
   'reserved', 0, '商标体系预留，当前专利报价系统不启用', 'trademark_reserved', 'Other', JSON_ARRAY('OTHER'),
   'WIPO_TREATIES', 'WIPO Treaty Portals', 'https://www.wipo.int/treaties/en/',
   'Current WIPO treaty pages', '商标体系预留；当前专利报价入口隐藏。', 0, 'pending_review', 1, 'CHF')
ON DUPLICATE KEY UPDATE
  display_code = VALUES(display_code),
  aliases_json = VALUES(aliases_json),
  reference_category = VALUES(reference_category),
  business_scope_json = VALUES(business_scope_json),
  visibility_scope = VALUES(visibility_scope),
  candidate_status = IF(jurisdiction_id IS NULL, VALUES(candidate_status), candidate_status),
  quote_selectable_default = VALUES(quote_selectable_default),
  not_selectable_reason = VALUES(not_selectable_reason),
  reserved_reason = VALUES(reserved_reason),
  source_id = VALUES(source_id),
  source_name = VALUES(source_name),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  source_note = VALUES(source_note),
  review_status = VALUES(review_status),
  is_active = VALUES(is_active);

UPDATE jurisdiction_reference_registry r
JOIN jurisdictions j ON UPPER(j.internal_code) = UPPER(r.standard_code)
  OR UPPER(j.display_code) = UPPER(r.display_code)
SET r.jurisdiction_id = j.jurisdiction_id,
    r.candidate_status = CASE
      WHEN r.candidate_status = 'candidate' THEN 'linked_formal_master'
      ELSE r.candidate_status
    END
WHERE r.jurisdiction_id IS NULL;
