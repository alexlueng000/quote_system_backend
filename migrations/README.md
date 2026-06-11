# SQL Migration Scripts

This folder contains the project SQL initialization, patch, acceptance-check, and rollback scripts.

Suggested reading order:

1. `mysql_init.sql`
2. `mysql_auth_update.sql`
3. `phase_1_*.sql` through `phase_9_*.sql`
4. `p0_ip_system_official_baseline.sql`
5. `*_fix*.sql` and `*_acceptance_check.sql`

Rollback scripts are kept next to their matching phase scripts with the `_rollback.sql` suffix.
