
# -*- coding: utf-8 -*-
# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from __future__ import annotations

import textwrap
from typing import List

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction


class Command(BaseCommand):
    help = "Adjust auto-increment / sequence next id for given physical tables."

    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.formatter_class = lambda prog: __import__('argparse').RawDescriptionHelpFormatter(prog)
        parser.description = textwrap.dedent("""
            Management command: adjust_auto_increment

            This command adjusts the auto-increment / sequence "next id" for one or more
            physical tables in a given Django database alias.

            Supported vendors:
            - MySQL: uses `ALTER TABLE <table> AUTO_INCREMENT = <value>`
            - PostgreSQL: uses `pg_get_serial_sequence` + `SELECT setval(seq, value, true)`

            Usage examples:

                # 1) Explicitly set next id for one table on target DB
                ./manage.py adjust_auto_increment \\
                    --db-alias target \\
                    --tables node_man_subscription \\
                    --next-id 200000

                # 2) Automatically set next id to MAX(id) + 1 for multiple tables
                ./manage.py adjust_auto_increment \\
                    --db-alias target \\
                    --tables node_man_subscription node_man_subscriptiontask \\
                    --from-max

                # 3) Dry-run mode (only prints SQL, does not execute)
                ./manage.py adjust_auto_increment \\
                    --db-alias target \\
                    --tables node_man_subscription \\
                    --next-id 200000 \\
                    --dry-run
            """)
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "--db-alias",
            dest="db_alias",
            default="default",
            help='Database alias defined in settings.DATABASES (default: "default").',
        )
        parser.add_argument(
            "--tables",
            dest="tables",
            nargs="+",
            required=True,
            help="Physical table name(s) whose auto-increment id will be adjusted.",
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--next-id",
            dest="next_id",
            type=int,
            help="Explicit next auto-increment id value to set.",
        )
        group.add_argument(
            "--from-max",
            dest="from_max",
            action="store_true",
            help="Compute next id as MAX(id) + 1 for each table.",
        )

        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Do not execute SQL; only print what would be executed.",
        )

    def handle(self, *args, **options):
        db_alias: str = options["db_alias"]
        tables: List[str] = options["tables"]
        next_id: int | None = options.get("next_id")
        from_max: bool = options.get("from_max", False)
        dry_run: bool = options.get("dry_run", False)

        if db_alias not in connections.databases:
            raise CommandError(
                f"Database alias `{db_alias}` is not configured in settings.DATABASES."
            )

        if next_id is None and not from_max:
            raise CommandError(
                "Either --next-id must be provided or --from-max must be set."
            )
        if next_id is not None and from_max:
            raise CommandError(
                "Options --next-id and --from-max are mutually exclusive."
            )

        conn = connections[db_alias]
        vendor = conn.vendor

        if vendor not in ("mysql", "postgresql"):
            raise CommandError(
                f"Unsupported database vendor `{vendor}`. "
                "Only MySQL and PostgreSQL are supported."
            )

        self.stdout.write(
            self.style.WARNING(
                f"Starting adjust_auto_increment: db_alias={db_alias}, "
                f"tables={tables}, vendor={vendor}, "
                f"mode={'from MAX(id)+1' if from_max else f'explicit next-id={next_id}'}, "
                f"dry_run={dry_run}"
            )
        )

        for table_name in tables:
            self._adjust_table_auto_increment(
                conn=conn,
                db_alias=db_alias,
                vendor=vendor,
                table_name=table_name,
                explicit_next_id=next_id,
                from_max=from_max,
                dry_run=dry_run,
            )

        self.stdout.write(self.style.SUCCESS("adjust_auto_increment finished."))

    def _adjust_table_auto_increment(
        self,
        conn,
        db_alias: str,
        vendor: str,
        table_name: str,
        explicit_next_id: int | None,
        from_max: bool,
        dry_run: bool,
    ) -> None:
        """
        Adjust auto-increment / sequence next id for a single table.
        """
        quoted_table = conn.ops.quote_name(table_name)

        # Determine target next id
        if from_max:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT MAX(id) FROM {quoted_table}")
                row = cursor.fetchone()
                max_id = row[0] if row and row[0] is not None else 0
            next_id_value = int(max_id) + 1
            self.stdout.write(
                f"[{db_alias}] Table `{table_name}`: MAX(id)={max_id}, "
                f"will set next id to {next_id_value}."
            )
        else:
            next_id_value = int(explicit_next_id)  # type: ignore[arg-type]
            self.stdout.write(
                f"[{db_alias}] Table `{table_name}`: explicit next id={next_id_value}."
            )

        # Build vendor-specific SQL
        if vendor == "mysql":
            sql = f"ALTER TABLE {quoted_table} AUTO_INCREMENT = %s"
            params = [next_id_value]
            human_desc = (
                f"ALTER TABLE {table_name} AUTO_INCREMENT = {next_id_value}"
            )
        elif vendor == "postgresql":
            # Determine sequence name for table.id
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_get_serial_sequence(%s, %s)", [table_name, "id"]
                )
                row = cursor.fetchone()
            if not row or not row[0]:
                raise CommandError(
                    f"[{db_alias}] Could not determine sequence for "
                    f"{table_name}.id using pg_get_serial_sequence. "
                    "Ensure the `id` column is backed by a sequence."
                )
            sequence_name = row[0]
            sql = "SELECT setval(%s, %s, true)"
            params = [sequence_name, next_id_value]
            human_desc = (
                f"SELECT setval('{sequence_name}', {next_id_value}, true) "
                f"for table {table_name}.id"
            )
        else:
            # Should be guarded earlier, but keep defensive code
            raise CommandError(f"Unsupported vendor `{vendor}`")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN][{db_alias}] Would execute: {human_desc}"
                )
            )
            return

        # Execute SQL in a transaction for safety
        with transaction.atomic(using=db_alias):
            with conn.cursor() as cursor:
                cursor.execute(sql, params)

        self.stdout.write(
            self.style.SUCCESS(
                f"[{db_alias}] Adjusted auto-increment for `{table_name}`: {human_desc}"
            )
        )