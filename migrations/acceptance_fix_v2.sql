USE quote_system;
SET NAMES utf8mb4;

ALTER TABLE quotation_drafts
  MODIFY status ENUM('草稿', '已合并正式报价', '已作废')
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '草稿';

ALTER TABLE quotation_draft_items
  MODIFY status ENUM('草稿', '已选择', '已合并正式报价', '已删除')
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '草稿';

ALTER TABLE countries
  MODIFY business_region VARCHAR(500)
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '';

UPDATE jurisdictions
SET display_code = 'EUIPO',
    name_cn = '欧盟知识产权局',
    name_en = 'European Union Intellectual Property Office',
    jurisdiction_type = 'regional_office'
WHERE internal_code = 'EM' OR display_code = 'EUIP0';

UPDATE countries
SET name_cn = '欧盟知识产权局',
    name_en = 'European Union Intellectual Property Office',
    country_type = '区域局',
    international_region = 'Europe',
    business_region = '["EUROPE","EU"]'
WHERE code = 'EM';

UPDATE countries
SET business_region = CASE code
    WHEN 'US' THEN '["NORTH_AMERICA","APEC"]'
    WHEN 'JP' THEN '["NORTHEAST_ASIA_JP_KR","APEC"]'
    WHEN 'KR' THEN '["NORTHEAST_ASIA_JP_KR","APEC"]'
    WHEN 'CN' THEN '["GREATER_CHINA","APEC"]'
    WHEN 'DE' THEN '["EUROPE","EU"]'
    WHEN 'EP' THEN '["EUROPE"]'
    WHEN 'EM' THEN '["EUROPE","EU"]'
    WHEN 'AU' THEN '["ANZ_OCEANIA","APEC"]'
    WHEN 'NZ' THEN '["ANZ_OCEANIA","APEC"]'
    WHEN 'SG' THEN '["SOUTHEAST_ASIA","ASEAN","APEC"]'
    ELSE business_region
  END
WHERE code IN ('US', 'JP', 'KR', 'CN', 'DE', 'EP', 'EM', 'AU', 'NZ', 'SG');
