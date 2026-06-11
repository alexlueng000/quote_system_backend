USE quote_system;
SET NAMES utf8mb4;

DELIMITER //

DROP PROCEDURE IF EXISTS add_column_if_missing //
CREATE PROCEDURE add_column_if_missing(
  IN table_name_value VARCHAR(128),
  IN column_name_value VARCHAR(128),
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
    SET @ddl = CONCAT('ALTER TABLE `', table_name_value, '` ADD COLUMN ', column_definition_value);
    PREPARE stmt FROM @ddl;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END //

DROP PROCEDURE IF EXISTS add_index_if_missing //
CREATE PROCEDURE add_index_if_missing(
  IN table_name_value VARCHAR(128),
  IN index_name_value VARCHAR(128),
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
    SET @ddl = CONCAT('ALTER TABLE `', table_name_value, '` ADD ', index_definition_value);
    PREPARE stmt FROM @ddl;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END //

DELIMITER ;

CALL add_column_if_missing(
  'ip_system_source_config',
  'source_scope',
  "`source_scope` VARCHAR(50) NOT NULL DEFAULT 'reference_only' AFTER `source_url`"
);
CALL add_column_if_missing(
  'ip_system_source_config',
  'official_source_name',
  "`official_source_name` VARCHAR(150) NOT NULL DEFAULT '' AFTER `source_scope`"
);
CALL add_column_if_missing(
  'ip_system_source_config',
  'parse_mode',
  "`parse_mode` VARCHAR(50) NOT NULL DEFAULT 'manual_reference' AFTER `parser_key`"
);
CALL add_column_if_missing(
  'jurisdictions',
  'is_deleted',
  '`is_deleted` TINYINT(1) NOT NULL DEFAULT 0 AFTER `is_enabled`'
);
CALL add_index_if_missing(
  'jurisdictions',
  'idx_jurisdictions_enabled_deleted',
  'KEY `idx_jurisdictions_enabled_deleted` (`is_enabled`, `is_deleted`)'
);

CREATE TABLE IF NOT EXISTS ip_system_relation_candidate (
  candidate_id VARCHAR(64) PRIMARY KEY,
  source_config_id VARCHAR(64) NULL,
  snapshot_id VARCHAR(64) NULL,
  batch_id VARCHAR(64) NULL,
  system_id VARCHAR(64) NOT NULL,
  business_domain VARCHAR(50) NOT NULL,
  relation_type_id VARCHAR(64) NULL,
  official_name VARCHAR(255) NOT NULL DEFAULT '',
  official_code VARCHAR(100) NOT NULL DEFAULT '',
  raw_text TEXT NULL,
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  source_reference VARCHAR(1000) NOT NULL DEFAULT '',
  evidence_text TEXT NULL,
  matched_jurisdiction_id VARCHAR(64) NULL,
  match_status VARCHAR(50) NOT NULL DEFAULT 'unmatched',
  match_confidence DECIMAL(6, 4) NULL,
  data_quality_flags_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ip_system_candidate_source (source_config_id, match_status),
  KEY idx_ip_system_candidate_batch (batch_id, match_status),
  KEY idx_ip_system_candidate_jurisdiction (matched_jurisdiction_id, match_status),
  KEY idx_ip_system_candidate_system (system_id, business_domain, match_status),
  KEY idx_ip_system_candidate_lookup (official_code, official_name(80)),
  CONSTRAINT fk_ip_system_candidate_source
    FOREIGN KEY (source_config_id) REFERENCES ip_system_source_config(source_config_id),
  CONSTRAINT fk_ip_system_candidate_snapshot
    FOREIGN KEY (snapshot_id) REFERENCES ip_system_source_snapshot(snapshot_id),
  CONSTRAINT fk_ip_system_candidate_batch
    FOREIGN KEY (batch_id) REFERENCES ip_system_sync_batch(batch_id),
  CONSTRAINT fk_ip_system_candidate_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_ip_system_candidate_relation_type
    FOREIGN KEY (relation_type_id) REFERENCES ip_system_relation_type(relation_type_id),
  CONSTRAINT fk_ip_system_candidate_jurisdiction
    FOREIGN KEY (matched_jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_p0_state_backup (
  backup_name VARCHAR(80) NOT NULL,
  entity_type VARCHAR(40) NOT NULL,
  entity_id VARCHAR(128) NOT NULL,
  business_domain VARCHAR(50) NOT NULL DEFAULT '',
  is_active TINYINT(1) NULL,
  is_enabled TINYINT(1) NULL,
  remark VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (backup_name, entity_type, entity_id, business_domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO ip_system_p0_state_backup (
  backup_name, entity_type, entity_id, business_domain, is_active, remark
)
SELECT
  'p0_first_batch_20260607',
  'ip_system_master',
  system_id,
  '',
  is_active,
  remark
FROM ip_system_master
WHERE system_code IN ('PCT', 'PARIS', 'EPC', 'EUIPO', 'HAGUE', 'UPC_UP', 'OAPI', 'ARIPO', 'MADRID');

INSERT IGNORE INTO ip_system_p0_state_backup (
  backup_name, entity_type, entity_id, business_domain, is_enabled, remark
)
SELECT
  'p0_first_batch_20260607',
  'ip_system_business_domain',
  system_id,
  business_domain,
  is_enabled,
  remark
FROM ip_system_business_domain
WHERE system_id IN (
  'ip-system-pct',
  'ip-system-paris',
  'ip-system-epc',
  'ip-system-euipo',
  'ip-system-hague',
  'ip-system-upc-up',
  'ip-system-oapi',
  'ip-system-aripo',
  'ip-system-madrid'
);

INSERT INTO ip_system_master (
  system_id, system_code, system_name_cn, system_name_en, system_category,
  business_domain_scope, is_active, display_order, default_update_frequency,
  source_priority, source_url, official_source_name, last_verified_at,
  next_review_due_at, remark
)
VALUES
  ('ip-system-pct', 'PCT', '专利合作条约', 'Patent Cooperation Treaty', 'international_treaty',
   'patent', 1, 10, 'annual', 'official_source_first', 'https://www.wipo.int/pct/en/pct_contracting_states.html', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 12 MONTH), 'P0 第一阶段启用；官方来源待复核。'),
  ('ip-system-paris', 'PARIS', '巴黎公约', 'Paris Convention', 'international_treaty',
   'general_ip', 1, 20, 'annual', 'official_source_first', 'https://www.wipo.int/treaties/en/ip/paris/', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 12 MONTH), 'P0 第一阶段启用；官方来源待复核。'),
  ('ip-system-epc', 'EPC', '欧洲专利公约', 'European Patent Convention', 'regional_patent_system',
   'patent', 1, 30, 'quarterly', 'official_source_first', 'https://www.epo.org/en/legal/epc', 'EPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), 'P0 第一阶段启用；EPC 是公约体系，EPO 是区域局对象。'),
  ('ip-system-euipo', 'EUIPO', '欧盟知识产权局', 'European Union Intellectual Property Office', 'regional_design_system',
   'design; trademark reserved', 1, 40, 'quarterly', 'official_source_first', 'https://www.euipo.europa.eu/', 'EUIPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), 'P0 第一阶段强制覆盖；不作为基础进入路径。'),
  ('ip-system-hague', 'HAGUE', '海牙外观设计体系', 'Hague System', 'regional_design_system',
   'design', 0, 50, 'quarterly', 'official_source_first', 'https://www.wipo.int/hague/en/members/', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), 'P0 inactive/reserved；Hague 放第二阶段或外观深化阶段。'),
  ('ip-system-upc-up', 'UPC_UP', '统一专利法院/单一专利', 'Unified Patent Court / Unitary Patent', 'court_or_unitary_effect_system',
   'patent', 0, 60, 'quarterly', 'official_source_first', 'https://www.unified-patent-court.org/', 'UPC', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), 'P0 inactive/reserved；UPC/UP 后续预留。'),
  ('ip-system-madrid', 'MADRID', '马德里商标国际注册体系', 'Madrid System', 'international_trademark_system',
   'trademark', 0, 65, 'quarterly', 'official_source_first', 'https://www.wipo.int/madrid/en/', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), 'P0 inactive/reserved；后续商标业务预留，不进入第一阶段验收。'),
  ('ip-system-oapi', 'OAPI', '非洲知识产权组织', 'African Intellectual Property Organization', 'regional_organization',
   'patent; design; trademark', 0, 70, 'semiannual', 'official_source_first', 'https://www.oapi.int/', 'OAPI', NULL, DATE_ADD(NOW(), INTERVAL 6 MONTH), 'P0 inactive/reserved；后续非欧美日韩扩展预留。'),
  ('ip-system-aripo', 'ARIPO', '非洲地区知识产权组织', 'African Regional Intellectual Property Organization', 'regional_organization',
   'patent; design; trademark', 0, 80, 'semiannual', 'official_source_first', 'https://www.aripo.org/', 'ARIPO', NULL, DATE_ADD(NOW(), INTERVAL 6 MONTH), 'P0 inactive/reserved；后续非欧美日韩扩展预留。')
ON DUPLICATE KEY UPDATE
  system_name_cn = VALUES(system_name_cn),
  system_name_en = VALUES(system_name_en),
  system_category = VALUES(system_category),
  business_domain_scope = VALUES(business_domain_scope),
  is_active = VALUES(is_active),
  display_order = VALUES(display_order),
  default_update_frequency = VALUES(default_update_frequency),
  source_priority = VALUES(source_priority),
  source_url = VALUES(source_url),
  official_source_name = VALUES(official_source_name),
  remark = VALUES(remark);

INSERT INTO ip_system_business_domain (
  id, system_id, business_domain, is_enabled,
  quote_hint_default_enabled, path_rule_default_dependency, remark
)
VALUES
  ('ipbd-pct-patent', 'ip-system-pct', 'patent', 1, 1, 1, 'P0 第一阶段 PCT 专利关系启用。'),
  ('ipbd-paris-general-ip', 'ip-system-paris', 'general_ip', 1, 1, 1, 'P0 第一阶段 Paris general_ip 关系启用。'),
  ('ipbd-epc-patent', 'ip-system-epc', 'patent', 1, 1, 1, 'P0 第一阶段 EPC 专利关系启用。'),
  ('ipbd-euipo-design', 'ip-system-euipo', 'design', 1, 1, 1, 'P0 第一阶段 EUIPO design 样例启用；不作为 entry_route。'),
  ('ipbd-euipo-trademark', 'ip-system-euipo', 'trademark', 0, 0, 0, '商标业务预留，P0 不启用。'),
  ('ipbd-hague-design', 'ip-system-hague', 'design', 0, 0, 0, 'Hague 第二阶段预留，P0 不启用。'),
  ('ipbd-upc-up-patent', 'ip-system-upc-up', 'patent', 0, 0, 0, 'UPC/UP 后续预留，P0 不启用。'),
  ('ipbd-madrid-trademark', 'ip-system-madrid', 'trademark', 0, 0, 0, 'Madrid 商标业务预留，P0 不启用。'),
  ('ipbd-oapi-patent', 'ip-system-oapi', 'patent', 0, 0, 0, 'OAPI 后续预留，P0 不启用。'),
  ('ipbd-oapi-design', 'ip-system-oapi', 'design', 0, 0, 0, 'OAPI 后续预留，P0 不启用。'),
  ('ipbd-oapi-trademark', 'ip-system-oapi', 'trademark', 0, 0, 0, 'OAPI 后续预留，P0 不启用。'),
  ('ipbd-aripo-patent', 'ip-system-aripo', 'patent', 0, 0, 0, 'ARIPO 后续预留，P0 不启用。'),
  ('ipbd-aripo-design', 'ip-system-aripo', 'design', 0, 0, 0, 'ARIPO 后续预留，P0 不启用。'),
  ('ipbd-aripo-trademark', 'ip-system-aripo', 'trademark', 0, 0, 0, 'ARIPO 后续预留，P0 不启用。')
ON DUPLICATE KEY UPDATE
  is_enabled = VALUES(is_enabled),
  quote_hint_default_enabled = VALUES(quote_hint_default_enabled),
  path_rule_default_dependency = VALUES(path_rule_default_dependency),
  remark = VALUES(remark);

INSERT INTO ip_system_relation_type (
  relation_type_id, relation_type_code, relation_type_name_cn,
  relation_type_name_en, applicable_system_category, is_active,
  display_order, remark
)
VALUES
  ('iprt-member-state', 'MEMBER_STATE', '成员国', 'Member State', 'regional_organization;regional_patent_system;regional_design_system;regional_trademark_system', 1, 10, ''),
  ('iprt-contracting-state', 'CONTRACTING_STATE', '缔约国', 'Contracting State', 'international_treaty;regional_patent_system;regional_design_system', 1, 20, ''),
  ('iprt-extension-state', 'EXTENSION_STATE', '延伸国', 'Extension State', 'regional_patent_system', 1, 30, '主要用于 EPC。'),
  ('iprt-validation-state', 'VALIDATION_STATE', '验证国/生效国', 'Validation State', 'regional_patent_system', 1, 40, '主要用于 EPC。'),
  ('iprt-designated-state', 'DESIGNATED_STATE', '指定国', 'Designated State', 'international_treaty', 1, 50, ''),
  ('iprt-covered-state', 'COVERED_STATE', '覆盖国', 'Covered State', 'regional_design_system;regional_trademark_system;court_or_unitary_effect_system', 1, 60, ''),
  ('iprt-participating-state', 'PARTICIPATING_STATE', '参与国', 'Participating State', 'court_or_unitary_effect_system;regional_organization', 1, 70, ''),
  ('iprt-receiving-office', 'RECEIVING_OFFICE', '受理局', 'Receiving Office', 'international_treaty', 1, 80, ''),
  ('iprt-regional-phase-office', 'REGIONAL_PHASE_OFFICE', '区域阶段进入/处理机构', 'Regional Phase Office', 'international_treaty', 1, 81, 'P0-7: PCT 区域阶段进入/处理机构；不得与 RECEIVING_OFFICE 受理局混淆。'),
  ('iprt-granting-authority', 'GRANTING_AUTHORITY', '区域授权机构', 'Granting Authority', 'regional_patent_system;regional_organization', 1, 82, 'P0-7: EPC/EPO 等区域授权机构语义；不是成员国。'),
  ('iprt-priority-route-available', 'PRIORITY_ROUTE_AVAILABLE', '优先权路径可用', 'Priority Route Available', 'international_treaty;regional_patent_system;regional_organization', 1, 83, 'P0-7: 只表达 Paris 优先权路径可用性，不表示 Paris 缔约国。'),
  ('iprt-regional-coverage', 'REGIONAL_COVERAGE', '区域覆盖范围', 'Regional Coverage', 'regional_patent_system;regional_organization;regional_design_system;regional_trademark_system', 1, 84, 'P0-7 预留：后续表达区域局覆盖国家/地区，本轮不落正式覆盖数据。'),
  ('iprt-former-member', 'FORMER_MEMBER', '前成员', 'Former Member', 'international_treaty;regional_organization;regional_patent_system;regional_design_system;court_or_unitary_effect_system', 1, 90, '')
ON DUPLICATE KEY UPDATE
  relation_type_name_cn = VALUES(relation_type_name_cn),
  relation_type_name_en = VALUES(relation_type_name_en),
  applicable_system_category = VALUES(applicable_system_category),
  is_active = VALUES(is_active),
  display_order = VALUES(display_order),
  remark = VALUES(remark);

INSERT INTO ip_system_source_config (
  source_config_id, system_id, source_name, source_type, source_url,
  source_scope, official_source_name, parser_key, parse_mode,
  update_frequency, auto_check_enabled, next_check_at,
  is_active, remark
)
VALUES
  ('ipsc-pct-official', 'ip-system-pct', 'WIPO PCT Contracting States', 'official_webpage', 'https://www.wipo.int/pct/en/pct_contracting_states.html', 'reference_only', 'WIPO', 'manual_reference', 'manual_reference', 'annual', 0, DATE_ADD(NOW(), INTERVAL 12 MONTH), 1, 'P0 official URL reference；样例需 sample_only / needs_official_confirmation。'),
  ('ipsc-paris-official', 'ip-system-paris', 'WIPO Paris Convention Members', 'official_webpage', 'https://www.wipo.int/treaties/en/ip/paris/', 'reference_only', 'WIPO', 'manual_reference', 'manual_reference', 'annual', 0, DATE_ADD(NOW(), INTERVAL 12 MONTH), 1, 'P0 official URL reference；样例需 sample_only / needs_official_confirmation。'),
  ('ipsc-epc-official', 'ip-system-epc', 'EPO EPC Contracting States', 'official_webpage', 'https://www.epo.org/en/legal/epc', 'reference_only', 'EPO', 'manual_reference', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'P0 official URL reference；EPC/EPO 口径需官方确认。'),
  ('ipsc-euipo-official', 'ip-system-euipo', 'EUIPO Official Website', 'official_webpage', 'https://www.euipo.europa.eu/', 'reference_only', 'EUIPO', 'manual_reference', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'P0 EUIPO 第一阶段强制 official URL reference；不作为 entry_route。'),
  ('ipsc-hague-official', 'ip-system-hague', 'WIPO Hague Members', 'official_webpage', 'https://www.wipo.int/hague/en/members/', 'reference_only', 'WIPO', 'manual_reference', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'Hague 第二阶段预留 official URL reference。'),
  ('ipsc-upc-up-official', 'ip-system-upc-up', 'UPC Official Website', 'official_webpage', 'https://www.unified-patent-court.org/', 'reference_only', 'UPC', 'manual_reference', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'UPC/UP 后续预留 official URL reference。'),
  ('ipsc-madrid-official', 'ip-system-madrid', 'WIPO Madrid System', 'official_webpage', 'https://www.wipo.int/madrid/en/', 'reference_only', 'WIPO', 'manual_reference', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'Madrid 商标业务预留 official URL reference。'),
  ('ipsc-oapi-official', 'ip-system-oapi', 'OAPI Official Website', 'official_webpage', 'https://www.oapi.int/', 'reference_only', 'OAPI', 'manual_reference', 'manual_reference', 'semiannual', 0, DATE_ADD(NOW(), INTERVAL 6 MONTH), 1, 'OAPI 后续预留 official URL reference。'),
  ('ipsc-aripo-official', 'ip-system-aripo', 'ARIPO Official Website', 'official_webpage', 'https://www.aripo.org/', 'reference_only', 'ARIPO', 'manual_reference', 'manual_reference', 'semiannual', 0, DATE_ADD(NOW(), INTERVAL 6 MONTH), 1, 'ARIPO 后续预留 official URL reference。')
ON DUPLICATE KEY UPDATE
  source_name = VALUES(source_name),
  source_type = VALUES(source_type),
  source_url = VALUES(source_url),
  source_scope = VALUES(source_scope),
  official_source_name = VALUES(official_source_name),
  parser_key = VALUES(parser_key),
  parse_mode = VALUES(parse_mode),
  update_frequency = VALUES(update_frequency),
  auto_check_enabled = VALUES(auto_check_enabled),
  is_active = VALUES(is_active),
  remark = VALUES(remark);

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
