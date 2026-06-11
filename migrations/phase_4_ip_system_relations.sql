USE quote_system;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS ip_system_master (
  system_id VARCHAR(64) PRIMARY KEY,
  system_code VARCHAR(50) NOT NULL,
  system_name_cn VARCHAR(150) NOT NULL,
  system_name_en VARCHAR(200) NOT NULL,
  system_category VARCHAR(80) NOT NULL,
  business_domain_scope VARCHAR(300) NOT NULL DEFAULT '',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  display_order INT NOT NULL DEFAULT 100,
  default_update_frequency VARCHAR(50) NOT NULL DEFAULT '',
  source_priority VARCHAR(50) NOT NULL DEFAULT '',
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  official_source_name VARCHAR(150) NOT NULL DEFAULT '',
  last_verified_at DATETIME NULL,
  next_review_due_at DATETIME NULL,
  remark VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ip_system_master_code (system_code),
  KEY idx_ip_system_master_active_order (is_active, display_order, system_code),
  KEY idx_ip_system_master_review_due (next_review_due_at, is_active),
  KEY idx_ip_system_master_category (system_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_business_domain (
  id VARCHAR(64) PRIMARY KEY,
  system_id VARCHAR(64) NOT NULL,
  business_domain VARCHAR(50) NOT NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  quote_hint_default_enabled TINYINT(1) NOT NULL DEFAULT 0,
  path_rule_default_dependency TINYINT(1) NOT NULL DEFAULT 0,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ip_system_business_domain (system_id, business_domain),
  KEY idx_ip_system_business_domain_enabled (business_domain, is_enabled),
  CONSTRAINT fk_ip_system_business_domain_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_relation_type (
  relation_type_id VARCHAR(64) PRIMARY KEY,
  relation_type_code VARCHAR(50) NOT NULL,
  relation_type_name_cn VARCHAR(100) NOT NULL,
  relation_type_name_en VARCHAR(150) NOT NULL,
  applicable_system_category VARCHAR(500) NOT NULL DEFAULT '',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  display_order INT NOT NULL DEFAULT 100,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ip_system_relation_type_code (relation_type_code),
  KEY idx_ip_system_relation_type_active_order (is_active, display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_source_config (
  source_config_id VARCHAR(64) PRIMARY KEY,
  system_id VARCHAR(64) NOT NULL,
  source_name VARCHAR(150) NOT NULL,
  source_type VARCHAR(50) NOT NULL,
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  source_scope VARCHAR(50) NOT NULL DEFAULT 'reference_only',
  official_source_name VARCHAR(150) NOT NULL DEFAULT '',
  parser_key VARCHAR(100) NOT NULL DEFAULT '',
  parse_mode VARCHAR(50) NOT NULL DEFAULT 'manual_reference',
  update_frequency VARCHAR(50) NOT NULL DEFAULT '',
  auto_check_enabled TINYINT(1) NOT NULL DEFAULT 0,
  last_checked_at DATETIME NULL,
  next_check_at DATETIME NULL,
  last_success_at DATETIME NULL,
  last_failed_at DATETIME NULL,
  failure_reason VARCHAR(1000) NOT NULL DEFAULT '',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  remark VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ip_system_source_config_system (system_id, is_active),
  KEY idx_ip_system_source_config_next_check (next_check_at, is_active),
  CONSTRAINT fk_ip_system_source_config_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_source_snapshot (
  snapshot_id VARCHAR(64) PRIMARY KEY,
  system_id VARCHAR(64) NOT NULL,
  source_config_id VARCHAR(64) NULL,
  snapshot_type VARCHAR(50) NOT NULL DEFAULT 'manual_import',
  raw_snapshot_path VARCHAR(1000) NOT NULL DEFAULT '',
  raw_content_hash VARCHAR(128) NOT NULL DEFAULT '',
  raw_metadata_json JSON NULL,
  captured_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  captured_by VARCHAR(255) NULL,
  remark VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ip_system_source_snapshot_system (system_id, captured_at),
  KEY idx_ip_system_source_snapshot_source (source_config_id, captured_at),
  CONSTRAINT fk_ip_system_source_snapshot_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_ip_system_source_snapshot_source_config
    FOREIGN KEY (source_config_id) REFERENCES ip_system_source_config(source_config_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_sync_batch (
  batch_id VARCHAR(64) PRIMARY KEY,
  system_id VARCHAR(64) NOT NULL,
  source_config_id VARCHAR(64) NULL,
  source_snapshot_id VARCHAR(64) NULL,
  batch_type VARCHAR(50) NOT NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'running',
  total_records_found INT NOT NULL DEFAULT 0,
  new_records_count INT NOT NULL DEFAULT 0,
  changed_records_count INT NOT NULL DEFAULT 0,
  removed_records_count INT NOT NULL DEFAULT 0,
  unchanged_records_count INT NOT NULL DEFAULT 0,
  exception_records_count INT NOT NULL DEFAULT 0,
  error_message VARCHAR(2000) NOT NULL DEFAULT '',
  raw_snapshot_path VARCHAR(1000) NOT NULL DEFAULT '',
  created_by VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ip_system_sync_batch_system (system_id, started_at),
  KEY idx_ip_system_sync_batch_status (status, started_at),
  KEY idx_ip_system_sync_batch_source (source_config_id, started_at),
  CONSTRAINT fk_ip_system_sync_batch_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_ip_system_sync_batch_source_config
    FOREIGN KEY (source_config_id) REFERENCES ip_system_source_config(source_config_id),
  CONSTRAINT fk_ip_system_sync_batch_snapshot
    FOREIGN KEY (source_snapshot_id) REFERENCES ip_system_source_snapshot(snapshot_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE IF NOT EXISTS jurisdiction_ip_system_relation (
  relation_id VARCHAR(64) PRIMARY KEY,
  jurisdiction_id VARCHAR(64) NOT NULL,
  system_id VARCHAR(64) NOT NULL,
  relation_type_id VARCHAR(64) NOT NULL,
  business_domain VARCHAR(50) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  effective_date DATE NULL,
  expiry_date DATE NULL,
  publish_status VARCHAR(50) NOT NULL DEFAULT 'published',
  published_at DATETIME NULL,
  published_by VARCHAR(255) NULL,
  source_reference VARCHAR(1000) NOT NULL DEFAULT '',
  source_snapshot_id VARCHAR(64) NULL,
  source_official_name VARCHAR(255) NOT NULL DEFAULT '',
  source_official_code VARCHAR(100) NOT NULL DEFAULT '',
  verification_status VARCHAR(50) NOT NULL DEFAULT 'published',
  verified_at DATETIME NULL,
  verified_by VARCHAR(255) NULL,
  quote_hint_enabled TINYINT(1) NOT NULL DEFAULT 0,
  path_rule_dependency TINYINT(1) NOT NULL DEFAULT 0,
  quote_hint_text VARCHAR(1000) NOT NULL DEFAULT '',
  special_statement TEXT NULL,
  data_quality_flags_json JSON NULL,
  admin_remark VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_jisr_jurisdiction_current (jurisdiction_id, publish_status, is_active, effective_date, expiry_date),
  KEY idx_jisr_system_current (system_id, business_domain, publish_status, is_active, effective_date, expiry_date),
  KEY idx_jisr_relation_match (jurisdiction_id, system_id, relation_type_id, business_domain),
  KEY idx_jisr_source_snapshot (source_snapshot_id),
  CONSTRAINT fk_jisr_jurisdiction
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id),
  CONSTRAINT fk_jisr_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_jisr_relation_type
    FOREIGN KEY (relation_type_id) REFERENCES ip_system_relation_type(relation_type_id),
  CONSTRAINT fk_jisr_source_snapshot
    FOREIGN KEY (source_snapshot_id) REFERENCES ip_system_source_snapshot(snapshot_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_change_review (
  review_id VARCHAR(64) PRIMARY KEY,
  batch_id VARCHAR(64) NOT NULL,
  system_id VARCHAR(64) NOT NULL,
  jurisdiction_id VARCHAR(64) NULL,
  relation_type_id VARCHAR(64) NULL,
  business_domain VARCHAR(50) NOT NULL DEFAULT '',
  change_type VARCHAR(50) NOT NULL,
  old_relation_id VARCHAR(64) NULL,
  old_value_json JSON NULL,
  new_value_json JSON NULL,
  source_official_name VARCHAR(255) NOT NULL DEFAULT '',
  source_official_code VARCHAR(100) NOT NULL DEFAULT '',
  data_quality_flags_json JSON NULL,
  review_status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
  reviewed_by VARCHAR(255) NULL,
  reviewed_at DATETIME NULL,
  published_by VARCHAR(255) NULL,
  published_at DATETIME NULL,
  review_comment VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ip_system_change_review_batch (batch_id, review_status),
  KEY idx_ip_system_change_review_system (system_id, review_status),
  KEY idx_ip_system_change_review_jurisdiction (jurisdiction_id, review_status),
  CONSTRAINT fk_ip_system_change_review_batch
    FOREIGN KEY (batch_id) REFERENCES ip_system_sync_batch(batch_id),
  CONSTRAINT fk_ip_system_change_review_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_ip_system_change_review_jurisdiction
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id),
  CONSTRAINT fk_ip_system_change_review_relation_type
    FOREIGN KEY (relation_type_id) REFERENCES ip_system_relation_type(relation_type_id),
  CONSTRAINT fk_ip_system_change_review_old_relation
    FOREIGN KEY (old_relation_id) REFERENCES jurisdiction_ip_system_relation(relation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_match_exception (
  exception_id VARCHAR(64) PRIMARY KEY,
  batch_id VARCHAR(64) NULL,
  system_id VARCHAR(64) NOT NULL,
  source_config_id VARCHAR(64) NULL,
  official_name VARCHAR(255) NOT NULL DEFAULT '',
  official_code VARCHAR(100) NOT NULL DEFAULT '',
  raw_record_json JSON NULL,
  suggested_jurisdiction_id VARCHAR(64) NULL,
  confidence_score DECIMAL(6, 4) NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  resolved_jurisdiction_id VARCHAR(64) NULL,
  resolved_by VARCHAR(255) NULL,
  resolved_at DATETIME NULL,
  resolution_comment VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ip_system_match_exception_filters (system_id, source_config_id, status),
  KEY idx_ip_system_match_exception_batch (batch_id, status),
  CONSTRAINT fk_ip_system_match_exception_batch
    FOREIGN KEY (batch_id) REFERENCES ip_system_sync_batch(batch_id),
  CONSTRAINT fk_ip_system_match_exception_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_ip_system_match_exception_source
    FOREIGN KEY (source_config_id) REFERENCES ip_system_source_config(source_config_id),
  CONSTRAINT fk_ip_system_match_exception_suggested
    FOREIGN KEY (suggested_jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id),
  CONSTRAINT fk_ip_system_match_exception_resolved
    FOREIGN KEY (resolved_jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_jurisdiction_alias_mapping (
  mapping_id VARCHAR(64) PRIMARY KEY,
  source_config_id VARCHAR(64) NULL,
  system_id VARCHAR(64) NOT NULL,
  official_name VARCHAR(255) NOT NULL DEFAULT '',
  official_code VARCHAR(100) NOT NULL DEFAULT '',
  jurisdiction_id VARCHAR(64) NOT NULL,
  match_method VARCHAR(50) NOT NULL DEFAULT 'manual_confirmed',
  confidence_score DECIMAL(6, 4) NULL,
  is_confirmed TINYINT(1) NOT NULL DEFAULT 0,
  confirmed_by VARCHAR(255) NULL,
  confirmed_at DATETIME NULL,
  remark VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ip_system_alias_mapping (system_id, source_config_id, official_name, official_code),
  KEY idx_ip_system_alias_mapping_lookup (system_id, official_code, official_name, is_confirmed),
  KEY idx_ip_system_alias_mapping_jurisdiction (jurisdiction_id, is_confirmed),
  CONSTRAINT fk_ip_system_alias_mapping_source
    FOREIGN KEY (source_config_id) REFERENCES ip_system_source_config(source_config_id),
  CONSTRAINT fk_ip_system_alias_mapping_system
    FOREIGN KEY (system_id) REFERENCES ip_system_master(system_id),
  CONSTRAINT fk_ip_system_alias_mapping_jurisdiction
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO ip_system_master (
  system_id, system_code, system_name_cn, system_name_en, system_category,
  business_domain_scope, is_active, display_order, default_update_frequency,
  source_priority, source_url, official_source_name, last_verified_at,
  next_review_due_at, remark
)
VALUES
  ('ip-system-pct', 'PCT', '专利合作条约', 'Patent Cooperation Treaty', 'international_treaty',
   'patent', 1, 10, 'annual', 'official_source_first', 'https://www.wipo.int/pct/en/pct_contracting_states.html', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 12 MONTH), 'PCT 成员关系较稳定，V1 使用手动导入/复核。'),
  ('ip-system-paris', 'PARIS', '巴黎公约', 'Paris Convention', 'international_treaty',
   'general_ip', 1, 20, 'annual', 'official_source_first', 'https://www.wipo.int/treaties/en/ip/paris/', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 12 MONTH), 'Paris 作为 general_ip 体系，不强绑 patent。'),
  ('ip-system-epc', 'EPC', '欧洲专利公约', 'European Patent Convention', 'regional_patent_system',
   'patent', 1, 30, 'quarterly', 'official_source_first', 'https://www.epo.org/en/legal/epc', 'EPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), '含成员国、延伸国、验证国等关系。'),
  ('ip-system-euipo', 'EUIPO', '欧盟知识产权局', 'European Union Intellectual Property Office', 'regional_design_system',
   'design; trademark reserved', 1, 40, 'quarterly', 'official_source_first', 'https://www.euipo.europa.eu/', 'EUIPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), 'V1 仅启用 design，trademark 预留但不启用。'),
  ('ip-system-hague', 'HAGUE', '海牙外观设计体系', 'Hague System', 'regional_design_system',
   'design', 0, 50, 'quarterly', 'official_source_first', 'https://www.wipo.int/hague/en/members/', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), '第二阶段或外观深化阶段预留，第一期不启用。'),
  ('ip-system-upc-up', 'UPC_UP', '统一专利法院/单一专利', 'Unified Patent Court / Unitary Patent', 'court_or_unitary_effect_system',
   'patent', 0, 60, 'quarterly', 'official_source_first', 'https://www.unified-patent-court.org/', 'UPC', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), '后续服务场景预留，第一期不启用。'),
  ('ip-system-madrid', 'MADRID', '马德里商标国际注册体系', 'Madrid System', 'international_trademark_system',
   'trademark', 0, 65, 'quarterly', 'official_source_first', 'https://www.wipo.int/madrid/en/', 'WIPO', NULL, DATE_ADD(NOW(), INTERVAL 3 MONTH), '商标国际注册预留，第一期专利新申请不启用。'),
  ('ip-system-oapi', 'OAPI', '非洲知识产权组织', 'African Intellectual Property Organization', 'regional_organization',
   'patent; design; trademark', 0, 70, 'semiannual', 'official_source_first', 'https://www.oapi.int/', 'OAPI', NULL, DATE_ADD(NOW(), INTERVAL 6 MONTH), '区域组织，已预留数据结构，暂未纳入第一期欧美日韩报价上线范围。'),
  ('ip-system-aripo', 'ARIPO', '非洲地区知识产权组织', 'African Regional Intellectual Property Organization', 'regional_organization',
   'patent; design; trademark', 0, 80, 'semiannual', 'official_source_first', 'https://www.aripo.org/', 'ARIPO', NULL, DATE_ADD(NOW(), INTERVAL 6 MONTH), '区域组织，已预留数据结构，暂未纳入第一期欧美日韩报价上线范围。')
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
  ('ipbd-pct-patent', 'ip-system-pct', 'patent', 1, 1, 1, 'PCT 专利业务启用。'),
  ('ipbd-paris-general-ip', 'ip-system-paris', 'general_ip', 1, 1, 1, 'Paris 按 general_ip 维护。'),
  ('ipbd-epc-patent', 'ip-system-epc', 'patent', 1, 1, 1, 'EPC 专利业务启用。'),
  ('ipbd-euipo-design', 'ip-system-euipo', 'design', 1, 1, 1, 'EUIPO V1 仅启用外观设计。'),
  ('ipbd-euipo-trademark', 'ip-system-euipo', 'trademark', 0, 0, 0, '商标业务预留，V1 不启用。'),
  ('ipbd-hague-design', 'ip-system-hague', 'design', 0, 0, 0, '海牙外观设计业务预留，第一期不启用。'),
  ('ipbd-upc-up-patent', 'ip-system-upc-up', 'patent', 0, 0, 0, 'UPC/UP 专利业务预留，第一期不启用。'),
  ('ipbd-madrid-trademark', 'ip-system-madrid', 'trademark', 0, 0, 0, 'Madrid 商标业务预留，第一期不启用。'),
  ('ipbd-oapi-patent', 'ip-system-oapi', 'patent', 0, 0, 0, 'OAPI 专利业务预留，第一期不启用。'),
  ('ipbd-oapi-design', 'ip-system-oapi', 'design', 0, 0, 0, 'OAPI 外观设计业务预留，第一期不启用。'),
  ('ipbd-oapi-trademark', 'ip-system-oapi', 'trademark', 0, 0, 0, 'OAPI 商标业务结构预留，第一期不启用。'),
  ('ipbd-aripo-patent', 'ip-system-aripo', 'patent', 0, 0, 0, 'ARIPO 专利业务预留，第一期不启用。'),
  ('ipbd-aripo-design', 'ip-system-aripo', 'design', 0, 0, 0, 'ARIPO 外观设计业务预留，第一期不启用。'),
  ('ipbd-aripo-trademark', 'ip-system-aripo', 'trademark', 0, 0, 0, 'ARIPO 商标业务结构预留，第一期不启用。')
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
  ('ipsc-pct-official', 'ip-system-pct', 'WIPO PCT Contracting States', 'official_webpage', 'https://www.wipo.int/pct/en/pct_contracting_states.html', 'reference_only', 'WIPO', 'manual_review', 'manual_reference', 'annual', 0, DATE_ADD(NOW(), INTERVAL 12 MONTH), 1, 'V1 优先作为官方 URL reference 维护。'),
  ('ipsc-paris-official', 'ip-system-paris', 'WIPO Paris Convention Members', 'official_webpage', 'https://www.wipo.int/treaties/en/ip/paris/', 'reference_only', 'WIPO', 'manual_review', 'manual_reference', 'annual', 0, DATE_ADD(NOW(), INTERVAL 12 MONTH), 1, 'V1 优先作为官方 URL reference 维护。'),
  ('ipsc-epc-official', 'ip-system-epc', 'EPO EPC Contracting States', 'official_webpage', 'https://www.epo.org/en/legal/epc', 'reference_only', 'EPO', 'manual_review', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'V1 优先作为官方 URL reference 维护。'),
  ('ipsc-euipo-official', 'ip-system-euipo', 'EUIPO Official Website', 'official_webpage', 'https://www.euipo.europa.eu/', 'reference_only', 'EUIPO', 'manual_review', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'V1 仅启用 design，优先作为官方 URL reference 维护。'),
  ('ipsc-hague-official', 'ip-system-hague', 'WIPO Hague Members', 'official_webpage', 'https://www.wipo.int/hague/en/members/', 'reference_only', 'WIPO', 'manual_review', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'V1 优先作为官方 URL reference 维护。'),
  ('ipsc-upc-up-official', 'ip-system-upc-up', 'UPC Official Website', 'official_webpage', 'https://www.unified-patent-court.org/', 'reference_only', 'UPC', 'manual_review', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, 'V1 优先作为官方 URL reference 维护。'),
  ('ipsc-madrid-official', 'ip-system-madrid', 'WIPO Madrid System', 'official_webpage', 'https://www.wipo.int/madrid/en/', 'reference_only', 'WIPO', 'manual_review', 'manual_reference', 'quarterly', 0, DATE_ADD(NOW(), INTERVAL 3 MONTH), 1, '商标业务预留官方来源，第一期不启用。'),
  ('ipsc-oapi-official', 'ip-system-oapi', 'OAPI Official Website', 'official_webpage', 'https://www.oapi.int/', 'reference_only', 'OAPI', 'manual_review', 'manual_reference', 'semiannual', 0, DATE_ADD(NOW(), INTERVAL 6 MONTH), 1, 'V1 记录官方来源，暂未纳入第一期上线范围。'),
  ('ipsc-aripo-official', 'ip-system-aripo', 'ARIPO Official Website', 'official_webpage', 'https://www.aripo.org/', 'reference_only', 'ARIPO', 'manual_review', 'manual_reference', 'semiannual', 0, DATE_ADD(NOW(), INTERVAL 6 MONTH), 1, 'V1 记录官方来源，暂未纳入第一期上线范围。')
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
