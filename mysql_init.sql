CREATE DATABASE IF NOT EXISTS quote_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE quote_system;

CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NULL,
  role ENUM('consultant', 'admin', 'approver') NOT NULL DEFAULT 'consultant',
  status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS countries (
  code VARCHAR(20) PRIMARY KEY,
  name_cn VARCHAR(100) NOT NULL,
  name_en VARCHAR(100) NOT NULL,
  default_currency VARCHAR(10) NOT NULL,
  application_language VARCHAR(100) NOT NULL DEFAULT '',
  application_cycle VARCHAR(100) NOT NULL DEFAULT '',
  has_substantive_examination TINYINT(1) NOT NULL DEFAULT 0,
  application_types_json JSON NULL,
  enable_entity_type TINYINT(1) NOT NULL DEFAULT 0,
  entity_type_options_json JSON NULL,
  enable_pct_route_detail TINYINT(1) NOT NULL DEFAULT 0,
  pct_route_detail_options_json JSON NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fee_rule_versions (
  id VARCHAR(64) PRIMARY KEY,
  version_name VARCHAR(100) NOT NULL,
  effective_date DATE NOT NULL,
  expires_at DATE NULL,
  is_current TINYINT(1) NOT NULL DEFAULT 1,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  created_by VARCHAR(36) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_fee_rule_versions_created_by
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fee_rules (
  id VARCHAR(64) PRIMARY KEY,
  version_id VARCHAR(64) NULL,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL,
  pct_route_detail VARCHAR(100) NOT NULL DEFAULT '',
  entity_type VARCHAR(100) NOT NULL DEFAULT '',
  stage VARCHAR(50) NOT NULL,
  item_group_key VARCHAR(100) NOT NULL DEFAULT '',
  item_name VARCHAR(100) NOT NULL,
  fee_type VARCHAR(50) NOT NULL,
  fee_category ENUM(
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
  ) NOT NULL DEFAULT '其他',
  amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  currency VARCHAR(10) NOT NULL,
  quote_currency VARCHAR(10) NOT NULL DEFAULT '',
  is_multi_currency TINYINT(1) NOT NULL DEFAULT 0,
  tax_included TINYINT(1) NOT NULL DEFAULT 0,
  is_default TINYINT(1) NOT NULL DEFAULT 1,
  trigger_condition VARCHAR(500) NOT NULL DEFAULT '',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  cost_nature ENUM('当前费用', '后续预估') NOT NULL,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_fee_rules_match (country_code, application_type, filing_route, is_active, is_default),
  KEY idx_fee_rules_version (version_id, country_code, application_type, filing_route),
  CONSTRAINT fk_fee_rules_version
    FOREIGN KEY (version_id) REFERENCES fee_rule_versions(id),
  CONSTRAINT fk_fee_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS translation_schemes (
  id VARCHAR(64) PRIMARY KEY,
  scheme_name VARCHAR(100) NOT NULL,
  is_recommended TINYINT(1) NOT NULL DEFAULT 0,
  needs_second_translation TINYINT(1) NOT NULL DEFAULT 0,
  applicable_countries_json JSON NULL,
  applicable_application_types_json JSON NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS translation_rules (
  id VARCHAR(64) PRIMARY KEY,
  scheme_id VARCHAR(64) NULL,
  item_name VARCHAR(100) NOT NULL,
  unit VARCHAR(20) NOT NULL,
  unit_price DECIMAL(14, 4) NOT NULL DEFAULT 0.0000,
  currency VARCHAR(10) NOT NULL,
  min_fee DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  is_default TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_translation_rules_scheme
    FOREIGN KEY (scheme_id) REFERENCES translation_schemes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_drafts (
  id VARCHAR(36) PRIMARY KEY,
  draft_no VARCHAR(50) NOT NULL UNIQUE,
  consultant_id VARCHAR(36) NULL,
  consultant_email VARCHAR(255) NOT NULL,
  consultant_name VARCHAR(100) NOT NULL,
  client_name VARCHAR(255) NOT NULL,
  client_contact VARCHAR(100) NOT NULL DEFAULT '',
  has_case TINYINT(1) NOT NULL DEFAULT 0,
  case_title VARCHAR(255) NOT NULL DEFAULT '',
  applicant_count INT NOT NULL DEFAULT 0,
  priority_count INT NOT NULL DEFAULT 0,
  claim_count INT NOT NULL DEFAULT 0,
  description_pages INT NOT NULL DEFAULT 0,
  drawing_pages INT NOT NULL DEFAULT 0,
  needs_translation TINYINT(1) NOT NULL DEFAULT 0,
  translation_scheme_id VARCHAR(64) NULL,
  translation_quantity_one DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  translation_quantity_two DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  status ENUM('草稿', '已合并正式报价', '已作废') NOT NULL DEFAULT '草稿',
  remark TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_quotation_drafts_consultant_email (consultant_email, status, created_at),
  CONSTRAINT fk_quotation_drafts_user
    FOREIGN KEY (consultant_id) REFERENCES users(id),
  CONSTRAINT fk_quotation_drafts_translation_scheme
    FOREIGN KEY (translation_scheme_id) REFERENCES translation_schemes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_draft_items (
  id VARCHAR(64) PRIMARY KEY,
  draft_id VARCHAR(36) NOT NULL,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL,
  pct_route_detail VARCHAR(100) NOT NULL DEFAULT '',
  entity_type VARCHAR(100) NOT NULL DEFAULT '',
  case_title VARCHAR(255) NOT NULL DEFAULT '',
  quote_currency VARCHAR(10) NOT NULL,
  current_stage_total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  future_stage_total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  total_amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  status ENUM('草稿', '已选择', '已合并正式报价', '已删除') NOT NULL DEFAULT '草稿',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_quotation_draft_items_draft (draft_id, sort_order),
  CONSTRAINT fk_quotation_draft_items_draft
    FOREIGN KEY (draft_id) REFERENCES quotation_drafts(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_quotation_draft_items_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotations (
  id VARCHAR(36) PRIMARY KEY,
  quotation_no VARCHAR(50) NOT NULL UNIQUE,
  source_draft_ids_json JSON NULL,
  consultant_id VARCHAR(36) NULL,
  consultant_email VARCHAR(255) NOT NULL,
  consultant_name VARCHAR(100) NOT NULL,
  client_name VARCHAR(255) NOT NULL,
  client_contact VARCHAR(100) NOT NULL DEFAULT '',
  country_code VARCHAR(20) NOT NULL,
  country_codes_json JSON NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL,
  currency VARCHAR(10) NOT NULL,
  has_case TINYINT(1) NOT NULL DEFAULT 0,
  case_title VARCHAR(255) NOT NULL DEFAULT '',
  applicant_count INT NOT NULL DEFAULT 0,
  priority_count INT NOT NULL DEFAULT 0,
  claim_count INT NOT NULL DEFAULT 0,
  description_pages INT NOT NULL DEFAULT 0,
  drawing_pages INT NOT NULL DEFAULT 0,
  needs_translation TINYINT(1) NOT NULL DEFAULT 0,
  translation_scheme_id VARCHAR(64) NULL,
  translation_quantity_one DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  translation_quantity_two DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  current_stage_total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  future_stage_total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  total_amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  status VARCHAR(50) NOT NULL DEFAULT '已生成报价',
  sent_at DATETIME NULL,
  next_followup_date DATE NULL,
  last_followup_at DATETIME NULL,
  close_reason VARCHAR(255) NOT NULL DEFAULT '',
  is_sent TINYINT(1) NOT NULL DEFAULT 0,
  is_confirmed TINYINT(1) NOT NULL DEFAULT 0,
  is_opened TINYINT(1) NOT NULL DEFAULT 0,
  opened_reference VARCHAR(100) NOT NULL DEFAULT '',
  remark TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_quotations_consultant_email (consultant_email),
  KEY idx_quotations_status (status),
  KEY idx_quotations_created_at (created_at),
  KEY idx_quotations_country (country_code),
  KEY idx_quotations_next_followup (next_followup_date, status),
  CONSTRAINT fk_quotations_user
    FOREIGN KEY (consultant_id) REFERENCES users(id),
  CONSTRAINT fk_quotations_country
    FOREIGN KEY (country_code) REFERENCES countries(code),
  CONSTRAINT fk_quotations_translation_scheme
    FOREIGN KEY (translation_scheme_id) REFERENCES translation_schemes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_items (
  id VARCHAR(64) PRIMARY KEY,
  quotation_id VARCHAR(36) NOT NULL,
  draft_item_id VARCHAR(64) NULL,
  country_code VARCHAR(20) NULL,
  application_type VARCHAR(50) NOT NULL DEFAULT '',
  filing_route VARCHAR(50) NOT NULL DEFAULT '',
  pct_route_detail VARCHAR(100) NOT NULL DEFAULT '',
  entity_type VARCHAR(100) NOT NULL DEFAULT '',
  case_title VARCHAR(255) NOT NULL DEFAULT '',
  stage VARCHAR(50) NOT NULL,
  item_group_key VARCHAR(100) NOT NULL DEFAULT '',
  item_name VARCHAR(100) NOT NULL,
  fee_type VARCHAR(50) NOT NULL,
  fee_category VARCHAR(100) NOT NULL DEFAULT '',
  amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  currency VARCHAR(10) NOT NULL,
  quote_currency VARCHAR(10) NOT NULL DEFAULT '',
  tax_included TINYINT(1) NOT NULL DEFAULT 0,
  cost_nature VARCHAR(50) NOT NULL,
  opening_status VARCHAR(50) NOT NULL DEFAULT '未开卷',
  not_opened_reason VARCHAR(255) NOT NULL DEFAULT '',
  remark VARCHAR(500) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_quotation_items_quotation (quotation_id, sort_order),
  KEY idx_quotation_items_country_opening (
    country_code,
    application_type,
    filing_route,
    opening_status
  ),
  CONSTRAINT fk_quotation_items_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_quotation_items_draft_item
    FOREIGN KEY (draft_item_id) REFERENCES quotation_draft_items(id),
  CONSTRAINT fk_quotation_items_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_followups (
  id VARCHAR(36) PRIMARY KEY,
  quotation_id VARCHAR(36) NOT NULL,
  quotation_item_id VARCHAR(64) NULL,
  user_id VARCHAR(36) NOT NULL,
  consultant_email VARCHAR(255) NOT NULL,
  followup_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  method VARCHAR(50) NOT NULL DEFAULT '邮件',
  content TEXT NOT NULL,
  next_followup_date DATE NULL,
  needs_meeting_report TINYINT(1) NOT NULL DEFAULT 0,
  meeting_report_status VARCHAR(50) NOT NULL DEFAULT '无需汇报',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_followups_next_date (next_followup_date, meeting_report_status),
  CONSTRAINT fk_followups_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_followups_quotation_item
    FOREIGN KEY (quotation_item_id) REFERENCES quotation_items(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_followups_user
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_openings (
  id VARCHAR(36) PRIMARY KEY,
  quotation_id VARCHAR(36) NOT NULL,
  quotation_item_id VARCHAR(64) NOT NULL,
  opening_type ENUM('个案开卷', '部分开卷') NOT NULL DEFAULT '个案开卷',
  opening_reference VARCHAR(100) NOT NULL DEFAULT '',
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL,
  case_title VARCHAR(255) NOT NULL DEFAULT '',
  opening_quantity INT NOT NULL DEFAULT 1,
  opening_template_json JSON NULL,
  opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(36) NULL,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  KEY idx_openings_stats (country_code, application_type, opened_at),
  CONSTRAINT fk_openings_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_openings_quotation_item
    FOREIGN KEY (quotation_item_id) REFERENCES quotation_items(id),
  CONSTRAINT fk_openings_country
    FOREIGN KEY (country_code) REFERENCES countries(code),
  CONSTRAINT fk_openings_created_by
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS framework_agreements (
  id VARCHAR(36) PRIMARY KEY,
  agreement_no VARCHAR(50) NOT NULL UNIQUE,
  quotation_id VARCHAR(36) NULL,
  client_name VARCHAR(255) NOT NULL,
  consultant_id VARCHAR(36) NULL,
  consultant_email VARCHAR(255) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  duration_months INT NOT NULL DEFAULT 0,
  covered_countries_json JSON NULL,
  covered_application_types_json JSON NULL,
  expected_opening_count INT NOT NULL DEFAULT 0,
  actual_opening_count INT NOT NULL DEFAULT 0,
  status ENUM('生效中', '已到期', '已终止') NOT NULL DEFAULT '生效中',
  remark TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_framework_agreements_period (status, start_date, end_date),
  CONSTRAINT fk_framework_agreements_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_framework_agreements_consultant
    FOREIGN KEY (consultant_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS framework_agreement_openings (
  id VARCHAR(36) PRIMARY KEY,
  agreement_id VARCHAR(36) NOT NULL,
  opening_id VARCHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_framework_agreement_openings_agreement
    FOREIGN KEY (agreement_id) REFERENCES framework_agreements(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_framework_agreement_openings_opening
    FOREIGN KEY (opening_id) REFERENCES quotation_openings(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_approval_requests (
  id VARCHAR(36) PRIMARY KEY,
  consultant_id VARCHAR(36) NOT NULL,
  consultant_email VARCHAR(255) NOT NULL,
  request_type ENUM('超过10条未转化继续报价') NOT NULL,
  open_unconverted_count INT NOT NULL DEFAULT 0,
  status ENUM('待审批', '已通过', '已拒绝', '已撤回') NOT NULL DEFAULT '待审批',
  reason TEXT NOT NULL,
  reviewer_id VARCHAR(36) NULL,
  reviewer_comment TEXT NULL,
  reviewed_at DATETIME NULL,
  valid_until DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_approval_requests_consultant (consultant_email, status, created_at),
  CONSTRAINT fk_approval_requests_consultant
    FOREIGN KEY (consultant_id) REFERENCES users(id),
  CONSTRAINT fk_approval_requests_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO users (id, name, email, password_hash, role, status)
VALUES
  ('u-consultant', 'Suri', 'suri@example.com', 'pbkdf2_sha256$200000$vP9OLI6rDyaIQ2UzY2K/XA==$3ky9VuoHkgV4guWfenesh7c51/I1iO/Ehamwl8RjY3o=', 'consultant', 'active'),
  ('u-admin', '管理员', 'admin@example.com', 'pbkdf2_sha256$200000$2Q5sF3OxGbhxDwRRQwOc7Q==$Wmma4UFaIU99y3UeW4JB/27br4QZDBgPKnZSSI7xwxY=', 'admin', 'active')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  password_hash = VALUES(password_hash),
  role = VALUES(role),
  status = VALUES(status);

INSERT INTO countries (
  code, name_cn, name_en, default_currency, application_language,
  application_cycle, has_substantive_examination, application_types_json,
  enable_entity_type, entity_type_options_json, enable_pct_route_detail,
  pct_route_detail_options_json, enabled
)
VALUES
  ('US', '美国', 'United States', 'USD', '英文', '12-36个月', 1, JSON_ARRAY('发明', '外观'), 1, JSON_ARRAY('大实体', '小实体', '微实体'), 1, JSON_ARRAY('30个月进入', '31个月进入'), 1),
  ('EP', '欧洲', 'Europe', 'EUR', '英文/法文/德文', '24-48个月', 1, JSON_ARRAY('发明'), 0, NULL, 1, JSON_ARRAY('31个月进入'), 1),
  ('JP', '日本', 'Japan', 'JPY', '日文', '18-36个月', 1, JSON_ARRAY('发明', '实用新型', '外观'), 0, NULL, 0, NULL, 1),
  ('KR', '韩国', 'Korea', 'KRW', '韩文', '18-36个月', 1, JSON_ARRAY('发明', '实用新型', '外观'), 0, NULL, 0, NULL, 1)
ON DUPLICATE KEY UPDATE
  name_cn = VALUES(name_cn),
  name_en = VALUES(name_en),
  default_currency = VALUES(default_currency),
  application_language = VALUES(application_language),
  application_cycle = VALUES(application_cycle),
  has_substantive_examination = VALUES(has_substantive_examination),
  application_types_json = VALUES(application_types_json),
  enable_entity_type = VALUES(enable_entity_type),
  entity_type_options_json = VALUES(entity_type_options_json),
  enable_pct_route_detail = VALUES(enable_pct_route_detail),
  pct_route_detail_options_json = VALUES(pct_route_detail_options_json),
  enabled = VALUES(enabled);

INSERT INTO fee_rule_versions (id, version_name, effective_date, is_current, remark, created_by)
VALUES
  ('2026-v1', '2026-V1 基础价格', '2026-06-01', 1, '初始化价格版本', 'u-admin')
ON DUPLICATE KEY UPDATE
  version_name = VALUES(version_name),
  effective_date = VALUES(effective_date),
  is_current = VALUES(is_current),
  remark = VALUES(remark);

INSERT INTO fee_rules (
  id, version_id, country_code, application_type, filing_route, stage,
  item_group_key, item_name, fee_type, fee_category, amount, currency,
  quote_currency, is_multi_currency, tax_included, is_default, trigger_condition,
  is_active, cost_nature, remark, sort_order
)
VALUES
  ('us-official-application', '2026-v1', 'US', '发明', 'PCT进入', '申请阶段', 'application', '官方申请费', '官方费', '官费', 1720.00, 'USD', 'USD', 0, 0, 1, '', 1, '当前费用', '', 10),
  ('us-foreign-service', '2026-v1', 'US', '发明', 'PCT进入', '申请阶段', 'application', '外所申请服务费', '外所费', '官费对应外所合作所服务费', 950.00, 'USD', 'USD', 0, 0, 1, '', 1, '当前费用', '', 20),
  ('us-local-service', '2026-v1', 'US', '发明', 'PCT进入', '申请阶段', 'application', '本所申请服务费', '本所费', '官费对应本所服务费', 4200.00, 'CNY', 'USD', 1, 1, 1, '', 1, '当前费用', '', 30),
  ('us-exam', '2026-v1', 'US', '发明', 'PCT进入', '审查阶段', 'examination', '请求实质审查费', '官方费', '官费', 880.00, 'USD', 'USD', 0, 0, 1, '', 1, '后续预估', '后续发生时确认', 40),
  ('us-grant', '2026-v1', 'US', '发明', 'PCT进入', '授权阶段', 'grant', '授权登记费', '官方费', '官费', 1200.00, 'USD', 'USD', 0, 0, 1, '', 1, '后续预估', '授权时确认', 50),
  ('ep-official-application', '2026-v1', 'EP', '发明', 'PCT进入', '申请阶段', 'application', '官方申请费', '官方费', '官费', 1495.00, 'EUR', 'EUR', 0, 0, 1, '', 1, '当前费用', '', 10),
  ('ep-foreign-service', '2026-v1', 'EP', '发明', 'PCT进入', '申请阶段', 'application', '外所申请服务费', '外所费', '官费对应外所合作所服务费', 1100.00, 'EUR', 'EUR', 0, 0, 1, '', 1, '当前费用', '', 20),
  ('ep-local-service', '2026-v1', 'EP', '发明', 'PCT进入', '申请阶段', 'application', '本所申请服务费', '本所费', '官费对应本所服务费', 4800.00, 'CNY', 'EUR', 1, 1, 1, '', 1, '当前费用', '', 30),
  ('ep-exam', '2026-v1', 'EP', '发明', 'PCT进入', '审查阶段', 'examination', '审查阶段预估费用', '官方费', '官费', 1915.00, 'EUR', 'EUR', 0, 0, 1, '', 1, '后续预估', '后续发生时确认', 40),
  ('jp-official-application', '2026-v1', 'JP', '发明', '巴黎公约', '申请阶段', 'application', '官方申请费', '官方费', '官费', 14000.00, 'JPY', 'JPY', 0, 0, 1, '', 1, '当前费用', '', 10),
  ('jp-foreign-service', '2026-v1', 'JP', '发明', '巴黎公约', '申请阶段', 'application', '外所申请服务费', '外所费', '官费对应外所合作所服务费', 120000.00, 'JPY', 'JPY', 0, 0, 1, '', 1, '当前费用', '', 20),
  ('jp-local-service', '2026-v1', 'JP', '发明', '巴黎公约', '申请阶段', 'application', '本所申请服务费', '本所费', '官费对应本所服务费', 3800.00, 'CNY', 'JPY', 1, 1, 1, '', 1, '当前费用', '', 30)
ON DUPLICATE KEY UPDATE
  version_id = VALUES(version_id),
  item_group_key = VALUES(item_group_key),
  fee_category = VALUES(fee_category),
  amount = VALUES(amount),
  currency = VALUES(currency),
  quote_currency = VALUES(quote_currency),
  is_multi_currency = VALUES(is_multi_currency),
  tax_included = VALUES(tax_included),
  is_default = VALUES(is_default),
  trigger_condition = VALUES(trigger_condition),
  is_active = VALUES(is_active),
  remark = VALUES(remark),
  sort_order = VALUES(sort_order);

INSERT INTO translation_schemes (
  id, scheme_name, is_recommended, needs_second_translation,
  applicable_countries_json, applicable_application_types_json, enabled, sort_order
)
VALUES
  ('recommended-standard', '推荐标准翻译方案', 1, 1, JSON_ARRAY('US', 'EP', 'JP', 'KR'), JSON_ARRAY('发明', '实用新型', '外观'), 1, 10)
ON DUPLICATE KEY UPDATE
  scheme_name = VALUES(scheme_name),
  is_recommended = VALUES(is_recommended),
  needs_second_translation = VALUES(needs_second_translation),
  applicable_countries_json = VALUES(applicable_countries_json),
  applicable_application_types_json = VALUES(applicable_application_types_json),
  enabled = VALUES(enabled),
  sort_order = VALUES(sort_order);

INSERT INTO translation_rules (
  id, scheme_id, item_name, unit, unit_price, currency, min_fee,
  enabled, is_default, sort_order
)
VALUES
  ('translation-main', 'recommended-standard', '申请文件翻译费', '词', 0.9000, 'CNY', 800.00, 1, 1, 10),
  ('translation-drawing', 'recommended-standard', '附图文字翻译/校对费', '页', 120.0000, 'CNY', 300.00, 1, 1, 20)
ON DUPLICATE KEY UPDATE
  scheme_id = VALUES(scheme_id),
  item_name = VALUES(item_name),
  unit = VALUES(unit),
  unit_price = VALUES(unit_price),
  currency = VALUES(currency),
  min_fee = VALUES(min_fee),
  enabled = VALUES(enabled),
  is_default = VALUES(is_default),
  sort_order = VALUES(sort_order);
