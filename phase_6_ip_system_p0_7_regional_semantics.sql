-- P0-7 regional office relationship semantics data-only patch.
-- No schema changes. This patch clarifies regional office relationships without
-- enabling pricing paths or reserved regional systems.

START TRANSACTION;

INSERT INTO ip_system_relation_type (
  relation_type_id, relation_type_code, relation_type_name_cn,
  relation_type_name_en, applicable_system_category, is_active,
  display_order, remark
)
VALUES
  ('iprt-regional-phase-office', 'REGIONAL_PHASE_OFFICE', '区域阶段进入/处理机构', 'Regional Phase Office', 'international_treaty', 1, 81, 'P0-7: PCT 区域阶段进入/处理机构；不得与 RECEIVING_OFFICE 受理局混淆。'),
  ('iprt-granting-authority', 'GRANTING_AUTHORITY', '区域授权机构', 'Granting Authority', 'regional_patent_system;regional_organization', 1, 82, 'P0-7: EPC/EPO 等区域授权机构语义；不是成员国。'),
  ('iprt-priority-route-available', 'PRIORITY_ROUTE_AVAILABLE', '优先权路径可用', 'Priority Route Available', 'international_treaty;regional_patent_system;regional_organization', 1, 83, 'P0-7: 只表达 Paris 优先权路径可用性，不表示 Paris 缔约国。'),
  ('iprt-regional-coverage', 'REGIONAL_COVERAGE', '区域覆盖范围', 'Regional Coverage', 'regional_patent_system;regional_organization;regional_design_system;regional_trademark_system', 1, 84, 'P0-7 预留：后续表达区域局覆盖国家/地区，本轮不落正式覆盖数据。')
ON DUPLICATE KEY UPDATE
  relation_type_name_cn = VALUES(relation_type_name_cn),
  relation_type_name_en = VALUES(relation_type_name_en),
  applicable_system_category = VALUES(applicable_system_category),
  is_active = VALUES(is_active),
  display_order = VALUES(display_order),
  remark = VALUES(remark);

UPDATE jurisdiction_ip_system_relation r
JOIN ip_system_master s ON s.system_id = r.system_id
JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
JOIN ip_system_relation_type rt_old ON rt_old.relation_type_id = r.relation_type_id
JOIN ip_system_relation_type rt_new ON rt_new.relation_type_code = 'GRANTING_AUTHORITY'
SET
  r.relation_type_id = rt_new.relation_type_id,
  r.source_official_name = 'European Patent Office',
  r.source_official_code = 'EP',
  r.verification_status = 'pending_review',
  r.quote_hint_enabled = 0,
  r.path_rule_dependency = 0,
  r.special_statement = 'P0-7 sample: EPC is the regional patent system; EPO/EP is shown as the regional granting authority, not as a member state or entry_route.',
  r.data_quality_flags_json = JSON_ARRAY('sample_only', 'needs_official_confirmation', 'p0_7_regional_semantics'),
  r.admin_remark = 'P0-7 corrected from MEMBER_STATE to GRANTING_AUTHORITY for EPC - EP/EPO regional office semantics.'
WHERE s.system_code = 'EPC'
  AND j.jurisdiction_id = 'jur-EP'
  AND rt_old.relation_type_code = 'MEMBER_STATE'
  AND r.business_domain = 'patent'
  AND r.source_reference = 'https://www.epo.org/en/legal/epc';

INSERT INTO jurisdiction_ip_system_relation (
  relation_id, jurisdiction_id, system_id, relation_type_id, business_domain,
  is_active, effective_date, expiry_date, publish_status, published_at, published_by,
  source_reference, source_official_name, source_official_code, verification_status,
  quote_hint_enabled, path_rule_dependency, quote_hint_text, special_statement,
  data_quality_flags_json, admin_remark
)
SELECT
  'iprel-p0-7-pct-ep-regional-phase-office', 'jur-EP', s.system_id, rt.relation_type_id, 'patent',
  1, NULL, NULL, 'published', NOW(), 'p0_7_patch',
  'https://www.wipo.int/pct/en/pct_contracting_states.html',
  'European Patent Office', 'EP', 'pending_review',
  0, 0, '',
  'P0-7 sample: EP/EPO can be shown as the PCT regional phase office for Euro-PCT; this is not PCT CONTRACTING_STATE and not entry_route.',
  JSON_ARRAY('sample_only', 'needs_official_confirmation', 'p0_7_regional_semantics'),
  'P0-7 EPO/EP regional phase office sample; OAPI/ARIPO/EAPO remain inactive/reserved.'
FROM ip_system_master s
JOIN ip_system_relation_type rt ON rt.relation_type_code = 'REGIONAL_PHASE_OFFICE'
WHERE s.system_code = 'PCT'
ON DUPLICATE KEY UPDATE
  relation_type_id = VALUES(relation_type_id),
  is_active = VALUES(is_active),
  publish_status = VALUES(publish_status),
  source_reference = VALUES(source_reference),
  source_official_name = VALUES(source_official_name),
  source_official_code = VALUES(source_official_code),
  verification_status = VALUES(verification_status),
  quote_hint_enabled = VALUES(quote_hint_enabled),
  path_rule_dependency = VALUES(path_rule_dependency),
  special_statement = VALUES(special_statement),
  data_quality_flags_json = VALUES(data_quality_flags_json),
  admin_remark = VALUES(admin_remark);

INSERT INTO jurisdiction_ip_system_relation (
  relation_id, jurisdiction_id, system_id, relation_type_id, business_domain,
  is_active, effective_date, expiry_date, publish_status, published_at, published_by,
  source_reference, source_official_name, source_official_code, verification_status,
  quote_hint_enabled, path_rule_dependency, quote_hint_text, special_statement,
  data_quality_flags_json, admin_remark
)
SELECT
  'iprel-p0-7-paris-ep-priority-route-available', 'jur-EP', s.system_id, rt.relation_type_id, 'general_ip',
  1, NULL, NULL, 'published', NOW(), 'p0_7_patch',
  'https://www.wipo.int/treaties/en/ip/paris/',
  'European Patent Office', 'EP', 'pending_review',
  0, 0, '',
  'P0-7 sample: Paris priority may be shown as available for EP/EPO applications; this is not Paris CONTRACTING_STATE and not entry_route.',
  JSON_ARRAY('sample_only', 'needs_official_confirmation', 'p0_7_regional_semantics'),
  'P0-7 EP/EPO Paris priority route availability sample; not a Paris contracting state relation.'
FROM ip_system_master s
JOIN ip_system_relation_type rt ON rt.relation_type_code = 'PRIORITY_ROUTE_AVAILABLE'
WHERE s.system_code = 'PARIS'
ON DUPLICATE KEY UPDATE
  relation_type_id = VALUES(relation_type_id),
  is_active = VALUES(is_active),
  publish_status = VALUES(publish_status),
  source_reference = VALUES(source_reference),
  source_official_name = VALUES(source_official_name),
  source_official_code = VALUES(source_official_code),
  verification_status = VALUES(verification_status),
  quote_hint_enabled = VALUES(quote_hint_enabled),
  path_rule_dependency = VALUES(path_rule_dependency),
  special_statement = VALUES(special_statement),
  data_quality_flags_json = VALUES(data_quality_flags_json),
  admin_remark = VALUES(admin_remark);

COMMIT;
