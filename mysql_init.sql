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
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fee_rules (
  id VARCHAR(64) PRIMARY KEY,
  country_code VARCHAR(20) NOT NULL,
  application_type VARCHAR(50) NOT NULL,
  filing_route VARCHAR(50) NOT NULL,
  stage VARCHAR(50) NOT NULL,
  item_name VARCHAR(100) NOT NULL,
  fee_type VARCHAR(50) NOT NULL,
  amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  currency VARCHAR(10) NOT NULL,
  is_default TINYINT(1) NOT NULL DEFAULT 1,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  cost_nature ENUM('当前费用', '后续预估') NOT NULL,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_fee_rules_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_fee_rules_match
  ON fee_rules(country_code, application_type, filing_route, is_active, is_default);

CREATE TABLE IF NOT EXISTS translation_rules (
  id VARCHAR(64) PRIMARY KEY,
  item_name VARCHAR(100) NOT NULL,
  unit VARCHAR(20) NOT NULL,
  unit_price DECIMAL(14, 4) NOT NULL DEFAULT 0.0000,
  currency VARCHAR(10) NOT NULL,
  min_fee DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  is_default TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotations (
  id VARCHAR(36) PRIMARY KEY,
  quotation_no VARCHAR(50) NOT NULL UNIQUE,
  consultant_id VARCHAR(36) NULL,
  consultant_email VARCHAR(255) NOT NULL,
  consultant_name VARCHAR(100) NOT NULL,
  client_name VARCHAR(255) NOT NULL,
  client_contact VARCHAR(100) NOT NULL DEFAULT '',
  country_code VARCHAR(20) NOT NULL,
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
  translation_quantity_one DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  translation_quantity_two DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  current_stage_total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  future_stage_total DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  total_amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  status ENUM('草稿', '已生成报价', '已发送客户', '跟进中', '需价格调整', '已确认', '已开卷', '未成交', '已作废') NOT NULL DEFAULT '已生成报价',
  is_sent TINYINT(1) NOT NULL DEFAULT 0,
  is_confirmed TINYINT(1) NOT NULL DEFAULT 0,
  is_opened TINYINT(1) NOT NULL DEFAULT 0,
  opened_reference VARCHAR(100) NOT NULL DEFAULT '',
  remark TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_quotations_user
    FOREIGN KEY (consultant_id) REFERENCES users(id),
  CONSTRAINT fk_quotations_country
    FOREIGN KEY (country_code) REFERENCES countries(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_quotations_consultant_email ON quotations(consultant_email);
CREATE INDEX idx_quotations_status ON quotations(status);
CREATE INDEX idx_quotations_created_at ON quotations(created_at);
CREATE INDEX idx_quotations_country ON quotations(country_code);

CREATE TABLE IF NOT EXISTS quotation_items (
  id VARCHAR(64) PRIMARY KEY,
  quotation_id VARCHAR(36) NOT NULL,
  stage VARCHAR(50) NOT NULL,
  item_name VARCHAR(100) NOT NULL,
  fee_type VARCHAR(50) NOT NULL,
  amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  currency VARCHAR(10) NOT NULL,
  cost_nature ENUM('当前费用', '后续预估') NOT NULL,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_quotation_items_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_quotation_items_quotation ON quotation_items(quotation_id, sort_order);

CREATE TABLE IF NOT EXISTS quotation_followups (
  id VARCHAR(36) PRIMARY KEY,
  quotation_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  followup_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  method ENUM('邮件', '电话', '微信', '会议', '其他') NOT NULL DEFAULT '邮件',
  content TEXT NOT NULL,
  next_followup_date DATE NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_followups_quotation
    FOREIGN KEY (quotation_id) REFERENCES quotations(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_followups_user
    FOREIGN KEY (user_id) REFERENCES users(id)
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

INSERT INTO countries (code, name_cn, name_en, default_currency, enabled)
VALUES
  ('US', '美国', 'United States', 'USD', 1),
  ('EP', '欧洲', 'Europe', 'EUR', 1),
  ('JP', '日本', 'Japan', 'JPY', 1),
  ('KR', '韩国', 'Korea', 'KRW', 1)
ON DUPLICATE KEY UPDATE
  name_cn = VALUES(name_cn),
  name_en = VALUES(name_en),
  default_currency = VALUES(default_currency),
  enabled = VALUES(enabled);

INSERT INTO fee_rules (
  id, country_code, application_type, filing_route, stage,
  item_name, fee_type, amount, currency, is_default, is_active,
  cost_nature, remark, sort_order
)
VALUES
  ('us-official-application', 'US', '发明', 'PCT进入', '申请阶段', '官方申请费', '官方费', 1720.00, 'USD', 1, 1, '当前费用', '', 10),
  ('us-foreign-service', 'US', '发明', 'PCT进入', '申请阶段', '外所申请服务费', '外所费', 950.00, 'USD', 1, 1, '当前费用', '', 20),
  ('us-local-service', 'US', '发明', 'PCT进入', '申请阶段', '本所申请服务费', '本所费', 4200.00, 'CNY', 1, 1, '当前费用', '', 30),
  ('us-exam', 'US', '发明', 'PCT进入', '审查阶段', '请求实质审查费', '官方费', 880.00, 'USD', 1, 1, '后续预估', '后续发生时确认', 40),
  ('us-grant', 'US', '发明', 'PCT进入', '授权阶段', '授权登记费', '官方费', 1200.00, 'USD', 1, 1, '后续预估', '授权时确认', 50),
  ('ep-official-application', 'EP', '发明', 'PCT进入', '申请阶段', '官方申请费', '官方费', 1495.00, 'EUR', 1, 1, '当前费用', '', 10),
  ('ep-foreign-service', 'EP', '发明', 'PCT进入', '申请阶段', '外所申请服务费', '外所费', 1100.00, 'EUR', 1, 1, '当前费用', '', 20),
  ('ep-local-service', 'EP', '发明', 'PCT进入', '申请阶段', '本所申请服务费', '本所费', 4800.00, 'CNY', 1, 1, '当前费用', '', 30),
  ('ep-exam', 'EP', '发明', 'PCT进入', '审查阶段', '审查阶段预估费用', '官方费', 1915.00, 'EUR', 1, 1, '后续预估', '后续发生时确认', 40),
  ('jp-official-application', 'JP', '发明', '巴黎公约', '申请阶段', '官方申请费', '官方费', 14000.00, 'JPY', 1, 1, '当前费用', '', 10),
  ('jp-foreign-service', 'JP', '发明', '巴黎公约', '申请阶段', '外所申请服务费', '外所费', 120000.00, 'JPY', 1, 1, '当前费用', '', 20),
  ('jp-local-service', 'JP', '发明', '巴黎公约', '申请阶段', '本所申请服务费', '本所费', 3800.00, 'CNY', 1, 1, '当前费用', '', 30)
ON DUPLICATE KEY UPDATE
  amount = VALUES(amount),
  currency = VALUES(currency),
  is_default = VALUES(is_default),
  is_active = VALUES(is_active),
  remark = VALUES(remark),
  sort_order = VALUES(sort_order);

INSERT INTO translation_rules (
  id, item_name, unit, unit_price, currency, min_fee,
  enabled, is_default, sort_order
)
VALUES
  ('translation-main', '申请文件翻译费', '词', 0.9000, 'CNY', 800.00, 1, 1, 10),
  ('translation-drawing', '附图文字翻译/校对费', '页', 120.0000, 'CNY', 300.00, 1, 1, 20)
ON DUPLICATE KEY UPDATE
  item_name = VALUES(item_name),
  unit = VALUES(unit),
  unit_price = VALUES(unit_price),
  currency = VALUES(currency),
  min_fee = VALUES(min_fee),
  enabled = VALUES(enabled),
  is_default = VALUES(is_default),
  sort_order = VALUES(sort_order);
