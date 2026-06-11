SELECT
  'P0-1 first_phase_jurisdiction_ids' AS check_name,
  c.code AS legacy_country_code,
  COALESCE(c.jurisdiction_id, m.jurisdiction_id) AS resolved_jurisdiction_id,
  j.internal_code,
  COALESCE(NULLIF(j.standard_code, ''), j.internal_code) AS standard_code,
  j.display_code,
  j.jurisdiction_type,
  j.is_enabled,
  COALESCE(j.is_deleted, 0) AS is_deleted_flag
FROM countries c
LEFT JOIN country_jurisdiction_map m ON m.country_code = c.code
LEFT JOIN jurisdictions j ON j.jurisdiction_id = COALESCE(c.jurisdiction_id, m.jurisdiction_id)
WHERE c.code IN ('US', 'JP', 'KR', 'EP')
ORDER BY c.code;

SELECT
  'P0-1 legacy_country_code_mapping_missing' AS check_name,
  c.code AS legacy_country_code,
  c.jurisdiction_id AS countries_jurisdiction_id,
  m.jurisdiction_id AS map_jurisdiction_id
FROM countries c
LEFT JOIN country_jurisdiction_map m ON m.country_code = c.code
WHERE c.code IN ('US', 'JP', 'KR', 'EP')
  AND COALESCE(c.jurisdiction_id, m.jurisdiction_id) IS NULL
ORDER BY c.code;

SELECT
  'P0-2 code_conflict_internal_display_standard' AS check_name,
  code_value,
  code_role,
  COUNT(*) AS duplicate_count
FROM (
  SELECT UPPER(internal_code) AS code_value, 'internal_code' AS code_role
  FROM jurisdictions
  WHERE COALESCE(internal_code, '') <> ''
  UNION ALL
  SELECT UPPER(display_code) AS code_value, 'display_code' AS code_role
  FROM jurisdictions
  WHERE COALESCE(display_code, '') <> ''
  UNION ALL
  SELECT UPPER(standard_code) AS code_value, 'standard_code' AS code_role
  FROM jurisdictions
  WHERE COALESCE(standard_code, '') <> ''
) code_pool
GROUP BY code_value, code_role
HAVING COUNT(*) > 1
ORDER BY code_role, code_value;

SELECT
  'P0-2 ep_epo_euipo_master_codes' AS check_name,
  j.jurisdiction_id,
  j.internal_code,
  COALESCE(NULLIF(j.standard_code, ''), j.internal_code) AS standard_code,
  j.display_code,
  j.name_cn,
  j.name_en,
  j.jurisdiction_type
FROM jurisdictions j
WHERE UPPER(j.internal_code) IN ('EP', 'EM')
   OR UPPER(j.display_code) IN ('EPO', 'EUIPO')
ORDER BY j.display_order, j.internal_code;

SELECT
  'P0-2 ip_system_codes' AS check_name,
  s.system_id,
  s.system_code,
  s.system_name_cn,
  s.system_name_en,
  s.system_category,
  s.is_active
FROM ip_system_master s
WHERE s.system_code IN ('EPC', 'EUIPO', 'UPC_UP')
ORDER BY s.display_order, s.system_code;

SELECT
  'P0-2 forbidden_entry_route_codes' AS check_name,
  r.id,
  r.country_code,
  r.application_type,
  r.filing_route
FROM country_path_rules r
WHERE UPPER(r.filing_route) IN ('EPC', 'EPO', 'EUIPO', 'UPC_UP', 'UPC', 'UP')
ORDER BY r.country_code, r.application_type, r.filing_route, r.id;

SELECT
  'P0-4 non_country_objects_without_legacy_mapping_expected' AS check_name,
  j.jurisdiction_id,
  j.internal_code,
  j.display_code,
  j.jurisdiction_type,
  m.country_code AS legacy_country_code
FROM jurisdictions j
LEFT JOIN country_jurisdiction_map m ON m.jurisdiction_id = j.jurisdiction_id
WHERE UPPER(j.internal_code) IN ('WO', 'PCT', 'HAGUE', 'MADRID')
   OR UPPER(j.display_code) IN ('WIPO', 'PCT', 'HAGUE', 'MADRID')
ORDER BY j.display_order, j.internal_code;

SELECT
  'P0-3 advisor_current_relation_with_disabled_or_deleted_jurisdiction' AS check_name,
  r.relation_id,
  r.jurisdiction_id,
  j.display_code,
  j.name_cn,
  j.is_enabled,
  COALESCE(j.is_deleted, 0) AS is_deleted_flag,
  s.system_code,
  rt.relation_type_code,
  r.business_domain,
  r.publish_status,
  r.is_active,
  r.effective_date,
  r.expiry_date
FROM jurisdiction_ip_system_relation r
JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
JOIN ip_system_master s ON s.system_id = r.system_id
JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
WHERE r.publish_status = 'published'
  AND r.is_active = 1
  AND (r.effective_date IS NULL OR r.effective_date <= CURRENT_DATE)
  AND (r.expiry_date IS NULL OR r.expiry_date >= CURRENT_DATE)
  AND (j.is_enabled = 0 OR COALESCE(j.is_deleted, 0) = 1)
ORDER BY s.system_code, j.display_code, rt.relation_type_code;

