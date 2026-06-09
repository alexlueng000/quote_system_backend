-- Rollback for P0-7 regional office relationship semantics data-only patch.
-- No schema changes are involved.

START TRANSACTION;

DELETE FROM jurisdiction_ip_system_relation
WHERE relation_id IN (
  'iprel-p0-7-pct-ep-regional-phase-office',
  'iprel-p0-7-paris-ep-priority-route-available'
);

UPDATE jurisdiction_ip_system_relation r
JOIN ip_system_master s ON s.system_id = r.system_id
JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
JOIN ip_system_relation_type rt_old ON rt_old.relation_type_id = r.relation_type_id
JOIN ip_system_relation_type rt_new ON rt_new.relation_type_code = 'MEMBER_STATE'
SET
  r.relation_type_id = rt_new.relation_type_id,
  r.source_official_name = 'European Patent Office',
  r.source_official_code = 'EP',
  r.verification_status = 'pending_review',
  r.special_statement = NULL,
  r.data_quality_flags_json = JSON_ARRAY('sample_only', 'needs_official_confirmation'),
  r.admin_remark = 'Rolled back P0-7 regional semantics patch.'
WHERE s.system_code = 'EPC'
  AND j.jurisdiction_id = 'jur-EP'
  AND rt_old.relation_type_code = 'GRANTING_AUTHORITY'
  AND r.business_domain = 'patent'
  AND r.source_reference = 'https://www.epo.org/en/legal/epc'
  AND JSON_CONTAINS(r.data_quality_flags_json, JSON_QUOTE('p0_7_regional_semantics'));

DELETE rt
FROM ip_system_relation_type rt
LEFT JOIN jurisdiction_ip_system_relation r ON r.relation_type_id = rt.relation_type_id
LEFT JOIN ip_system_relation_candidate c ON c.relation_type_id = rt.relation_type_id
LEFT JOIN ip_system_change_review cr ON cr.relation_type_id = rt.relation_type_id
WHERE rt.relation_type_code IN (
  'REGIONAL_PHASE_OFFICE',
  'GRANTING_AUTHORITY',
  'PRIORITY_ROUTE_AVAILABLE',
  'REGIONAL_COVERAGE'
)
  AND r.relation_id IS NULL
  AND c.candidate_id IS NULL
  AND cr.review_id IS NULL;

COMMIT;
