USE quote_system;

ALTER TABLE users
  ADD COLUMN password_hash VARCHAR(255) NULL AFTER email;

UPDATE users
SET password_hash = 'pbkdf2_sha256$200000$vP9OLI6rDyaIQ2UzY2K/XA==$3ky9VuoHkgV4guWfenesh7c51/I1iO/Ehamwl8RjY3o='
WHERE email = 'suri@example.com';

UPDATE users
SET password_hash = 'pbkdf2_sha256$200000$2Q5sF3OxGbhxDwRRQwOc7Q==$Wmma4UFaIU99y3UeW4JB/27br4QZDBgPKnZSSI7xwxY='
WHERE email = 'admin@example.com';

