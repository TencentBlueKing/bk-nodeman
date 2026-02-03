# -*- coding: utf-8 -*-
"""
Database router to prevent Django's migrate command from operating on
the `source` and `target` database aliases used for incremental migration.

Usage:
1. Place this file under `script_tools/tenant_migrate/` (already done).
2. In your Django settings add:

    DATABASE_ROUTERS = [
        'script_tools.tenant_migrate.no_migrate_router.NoMigrateRouter',
    ]

This router only affects migration operations (`manage.py migrate`).
It returns `False` for `allow_migrate` on the configured DB aliases,
so migrations won't be applied to them. Other DB operations (read/write)
are unaffected.
"""

class NoMigrateRouter:
    """Prevent migrations on the source/target DBs."""

    DISABLED_DBS = {"source", "target"}

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Return False to disallow migrations on configured DBs.

        Django will fall back to default behavior if None is returned.
        """
        if db in self.DISABLED_DBS:
            return False
        return None
