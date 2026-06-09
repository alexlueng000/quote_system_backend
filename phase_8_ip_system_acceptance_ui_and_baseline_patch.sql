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

DELIMITER ;

CREATE TABLE IF NOT EXISTS ip_system_data_source (
  id VARCHAR(64) PRIMARY KEY,
  system_code VARCHAR(50) NOT NULL,
  source_name VARCHAR(150) NOT NULL,
  source_type VARCHAR(50) NOT NULL,
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  purpose_note VARCHAR(1000) NOT NULL DEFAULT '',
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  last_checked_at DATETIME NULL,
  last_success_at DATETIME NULL,
  last_check_status VARCHAR(50) NOT NULL DEFAULT '',
  last_check_message VARCHAR(1000) NOT NULL DEFAULT '',
  last_check_summary VARCHAR(1000) NOT NULL DEFAULT '',
  last_update_summary VARCHAR(1000) NOT NULL DEFAULT '',
  admin_update_note VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ip_system_data_source_system (system_code, is_enabled),
  KEY idx_ip_system_data_source_type (source_type, is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_non_membership_baseline (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  source_id VARCHAR(64) NOT NULL DEFAULT '',
  source_type VARCHAR(50) NOT NULL DEFAULT '',
  system_code VARCHAR(50) NOT NULL DEFAULT '',
  object_code VARCHAR(20) NOT NULL DEFAULT '',
  object_name_zh VARCHAR(150) NOT NULL DEFAULT '',
  object_name_en VARCHAR(200) NOT NULL DEFAULT '',
  object_type VARCHAR(50) NOT NULL DEFAULT '',
  baseline_kind VARCHAR(80) NOT NULL DEFAULT '',
  relation_type VARCHAR(80) NOT NULL DEFAULT '',
  route_type VARCHAR(80) NOT NULL DEFAULT '',
  regional_system_code VARCHAR(50) NOT NULL DEFAULT '',
  system_hint VARCHAR(1000) NOT NULL DEFAULT '',
  profile_url VARCHAR(500) NOT NULL DEFAULT '',
  source_name VARCHAR(150) NOT NULL DEFAULT '',
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  internal_remark VARCHAR(1000) NOT NULL DEFAULT '',
  effective_date DATE NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ip_non_membership_baseline (
    source_id, source_type, system_code, object_code, baseline_kind,
    relation_type, route_type, regional_system_code
  ),
  KEY idx_ip_non_membership_source (source_id, is_active),
  KEY idx_ip_non_membership_object (object_code, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ip_system_update_history (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  source_id VARCHAR(64) NOT NULL DEFAULT '',
  system_code VARCHAR(50) NOT NULL DEFAULT '',
  source_name VARCHAR(150) NOT NULL DEFAULT '',
  source_type VARCHAR(50) NOT NULL DEFAULT '',
  operation VARCHAR(50) NOT NULL DEFAULT '',
  update_type VARCHAR(120) NOT NULL DEFAULT '',
  update_count INT NOT NULL DEFAULT 0,
  parsed_count INT NULL,
  parsed_date_count INT NULL,
  written_date_count INT NULL,
  system_summary VARCHAR(2000) NOT NULL DEFAULT '',
  admin_note VARCHAR(1000) NOT NULL DEFAULT '',
  actor VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(50) NOT NULL DEFAULT '',
  failure_reason VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ip_update_history_source (source_id, created_at),
  KEY idx_ip_update_history_system (system_code, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CALL add_column_if_missing('ip_system_official_members', 'membership_relation_type', '`membership_relation_type` VARCHAR(80) NOT NULL DEFAULT '''' AFTER `member_type`');
CALL add_column_if_missing('ip_system_official_members', 'pct_route_type', '`pct_route_type` VARCHAR(80) NOT NULL DEFAULT '''' AFTER `membership_relation_type`');
CALL add_column_if_missing('ip_system_official_members', 'regional_system_code', '`regional_system_code` VARCHAR(50) NOT NULL DEFAULT '''' AFTER `pct_route_type`');
CALL add_column_if_missing('ip_system_official_members', 'route_remark', '`route_remark` VARCHAR(1000) NOT NULL DEFAULT '''' AFTER `regional_system_code`');
CALL add_column_if_missing('ip_system_official_members', 'internal_remark', '`internal_remark` VARCHAR(1000) NOT NULL DEFAULT '''' AFTER `remark`');
CALL add_column_if_missing('ip_system_official_members', 'remark_updated_at', '`remark_updated_at` DATETIME NULL AFTER `internal_remark`');
CALL add_column_if_missing('ip_system_official_members', 'remark_updated_by', '`remark_updated_by` VARCHAR(255) NOT NULL DEFAULT '''' AFTER `remark_updated_at`');
CALL add_column_if_missing('ip_system_data_source', 'last_check_status', '`last_check_status` VARCHAR(50) NOT NULL DEFAULT '''' AFTER `last_success_at`');
CALL add_column_if_missing('ip_system_data_source', 'last_check_message', '`last_check_message` VARCHAR(1000) NOT NULL DEFAULT '''' AFTER `last_check_status`');
CALL add_column_if_missing('ip_system_data_source', 'last_check_summary', '`last_check_summary` VARCHAR(1000) NOT NULL DEFAULT '''' AFTER `last_check_message`');
CALL add_column_if_missing('ip_system_data_source', 'last_update_summary', '`last_update_summary` VARCHAR(1000) NOT NULL DEFAULT '''' AFTER `last_check_summary`');
CALL add_column_if_missing('ip_system_data_source', 'admin_update_note', '`admin_update_note` VARCHAR(1000) NOT NULL DEFAULT '''' AFTER `last_update_summary`');

INSERT INTO ip_system_data_source (
  id, system_code, source_name, source_type, source_url, purpose_note, is_enabled
)
VALUES
  ('ipds-pct-contracting-states', 'PCT', 'WIPO PCT Contracting States', 'treaty_membership_source', 'https://www.wipo.int/en/web/pct-system/pct_contracting_states', 'PCT 正式缔约国数据；用于 PCT 成员关系判断，未来生效对象不计入当前成员。', 1),
  ('ipds-pct-regional-designations', 'PCT', 'WIPO PCT Regional Designations', 'regional_route_source', 'https://www.wipo.int/zh/web/pct-system/texts/reg_des', 'PCT 区域指定/区域阶段路径提示；不生成 PCT 缔约国。', 1),
  ('ipds-paris-contracting-parties', 'PARIS', 'WIPO Lex Paris Convention Contracting Parties', 'treaty_membership_source', 'https://www.wipo.int/wipolex/en/treaties/ShowResults?search_what=C&treaty_id=2', 'Paris Convention 181 个缔约方正式成员数据；用于成员计数和成员关系判断。', 1),
  ('ipds-paris-non-pct-route', 'PARIS', 'WIPO States bound by the Paris Convention but not the PCT', 'paris_non_pct_route_source', 'https://www.wipo.int/en/web/pct-system/paris_non_pct', '识别属于巴黎公约成员但不是 PCT 缔约国的国家；不生成 PCT 成员关系，不影响 Paris 181 计数。', 1),
  ('ipds-wipolex-members', 'REFERENCE', 'WIPO Lex 管辖区/组织参考名录', 'reference_source', 'https://www.wipo.int/wipolex/zh/members', '202 个 WIPO Lex 管辖区/组织参考对象；用于参考对象覆盖看板；不生成任何条约成员关系。', 1),
  ('ipds-epc-member-states', 'EPC', 'EPO Member States', 'treaty_membership_source', 'https://www.epo.org/en/about-us/foundation/member-states', 'EPC 成员国数据；延伸/生效关系单独展示，不混入成员国计数。', 1),
  ('ipds-eu-design-members', 'EU_DESIGN', 'EUIPO / European Union member countries', 'design_scope_source', 'https://european-union.europa.eu/principles-countries-history/eu-countries_en', '欧盟外观设计适用成员国范围数据。', 1)
ON DUPLICATE KEY UPDATE
  system_code = VALUES(system_code),
  source_name = VALUES(source_name),
  source_type = VALUES(source_type),
  source_url = VALUES(source_url),
  purpose_note = VALUES(purpose_note),
  is_enabled = VALUES(is_enabled);

UPDATE ip_system_official_members
SET membership_relation_type = CASE
  WHEN system_code = 'PCT' THEN 'pct_contracting_state'
  WHEN system_code = 'PARIS' THEN 'paris_contracting_party'
  WHEN system_code = 'EPC' THEN 'epc_member_state'
  WHEN system_code = 'EU_DESIGN' THEN 'covered_state'
  ELSE membership_relation_type
END
WHERE membership_relation_type = '';

UPDATE ip_system_official_members
SET remark = ''
WHERE system_code = 'EU_DESIGN'
  AND remark IN (
    '按欧盟成员资格适用。',
    '按欧盟成员资格适用；欧盟外观设计权利在欧盟成员国范围内适用。'
  );

UPDATE ip_system_official_members
SET is_confirmed = 0,
    remark = '未来生效 PCT 对象；不计入当前 PCT 成员。'
WHERE system_code = 'PCT'
  AND is_confirmed = 1
  AND effective_date IS NOT NULL
  AND effective_date > CURDATE();

-- Data rows for PCT / Paris dates and non-membership route/reference/scope
-- baselines are intentionally refreshed by the idempotent application apply
-- endpoints after this schema patch:
--   /api/v1/ip-system-query/data-sources/{source_id}/check-updates
--   /api/v1/ip-system-query/data-sources/{source_id}/apply-updates
-- This keeps official-date parsing tied to the current official source parser
-- instead of freezing 158/181 dates into a migration file.

DROP PROCEDURE IF EXISTS add_column_if_missing;
