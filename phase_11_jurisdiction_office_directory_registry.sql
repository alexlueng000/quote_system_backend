-- V1.1-B repair: WIPO IP Offices Directory mapping layer.
-- This table is a directory mapping registry, not a second jurisdiction master.
-- The backend runtime seed mirrors the WIPO directory for the full COUNTRY_NAMES
-- candidate pool; this migration keeps representative rows for direct SQL bootstrap.

CREATE TABLE IF NOT EXISTS jurisdiction_office_directory_registry (
  country_code VARCHAR(16) NOT NULL,
  jurisdiction_code VARCHAR(16) NOT NULL,
  country_name_en VARCHAR(255) NOT NULL,
  office_role VARCHAR(64) NOT NULL,
  office_name_en VARCHAR(255) NOT NULL,
  office_name_cn VARCHAR(255) NOT NULL DEFAULT '',
  office_display_code VARCHAR(64) NOT NULL DEFAULT '',
  office_type VARCHAR(64) NOT NULL,
  source_id VARCHAR(128) NOT NULL,
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  source_version VARCHAR(255) NOT NULL DEFAULT '',
  review_status VARCHAR(64) NOT NULL DEFAULT 'pending_review',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  source_note TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (country_code),
  KEY idx_jurisdiction_office_directory_code (jurisdiction_code),
  KEY idx_jurisdiction_office_directory_source (source_id, is_active),
  CONSTRAINT fk_jurisdiction_office_directory_source
    FOREIGN KEY (source_id) REFERENCES jurisdiction_data_source_registry(source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO jurisdiction_office_directory_registry (
  country_code, jurisdiction_code, country_name_en, office_role,
  office_name_en, office_name_cn, office_display_code, office_type,
  source_id, source_url, source_version, review_status, is_active, source_note
)
VALUES
  ('NL', 'NL', 'Netherlands', 'default_receiving_office', 'Netherlands Patent Office', '荷兰专利局', '', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1,
   'WIPO Directory of IP Offices lists Netherlands Patent Office; no office abbreviation is forced.'),
  ('CA', 'CA', 'Canada', 'default_receiving_office', 'Canadian Intellectual Property Office', '加拿大知识产权局', 'CIPO', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1,
   'WIPO Directory of IP Offices lists Canadian Intellectual Property Office; CIPO retained as reviewed display abbreviation.'),
  ('CN', 'CN', 'China', 'default_receiving_office', 'China National Intellectual Property Administration', '国家知识产权局', 'CNIPA', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('US', 'US', 'United States of America', 'default_receiving_office', 'United States Patent and Trademark Office', '美国专利商标局', 'USPTO', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('JP', 'JP', 'Japan', 'default_receiving_office', 'Japan Patent Office', '日本特许厅', 'JPO', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('KR', 'KR', 'Republic of Korea', 'default_receiving_office', 'Ministry of Intellectual Property', '韩国知识产权部', 'MOIP', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1,
   'Current WIPO profile lists Ministry of Intellectual Property (MOIP); KIPO retained only as historical/search alias.'),
  ('DE', 'DE', 'Germany', 'default_receiving_office', 'German Patent and Trade Mark Office', '德国专利商标局', 'DPMA', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('CO', 'CO', 'Colombia', 'default_receiving_office', 'Superintendence of Industry and Commerce', '哥伦比亚工业和商业监督局', 'SIC', 'national_ip_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('EP', 'EP', 'European Patent Organisation', 'regional_office', 'European Patent Office', '欧洲专利局', 'EPO', 'regional_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('EM', 'EM', 'European Union', 'regional_office', 'European Union Intellectual Property Office', '欧盟知识产权局', 'EUIPO', 'regional_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, ''),
  ('WO', 'WO', 'World Intellectual Property Organization', 'international_office', 'International Bureau of WIPO', '世界知识产权组织国际局', 'WIPO/IB', 'international_office',
   'WIPO_IP_OFFICES_DIRECTORY', 'https://www.wipo.int/en/web/country-profiles/directory-ip-offices', 'WIPO Country Profiles - Directory of IP Offices current', 'pending_review', 1, '')
ON DUPLICATE KEY UPDATE
  jurisdiction_code = VALUES(jurisdiction_code),
  country_name_en = VALUES(country_name_en),
  office_role = VALUES(office_role),
  office_name_en = VALUES(office_name_en),
  office_name_cn = VALUES(office_name_cn),
  office_display_code = VALUES(office_display_code),
  office_type = VALUES(office_type),
  source_id = VALUES(source_id),
  source_url = VALUES(source_url),
  source_version = VALUES(source_version),
  review_status = VALUES(review_status),
  is_active = VALUES(is_active),
  source_note = VALUES(source_note);
