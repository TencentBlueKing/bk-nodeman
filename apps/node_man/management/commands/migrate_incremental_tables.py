# -*- coding: utf-8 -*-

from __future__ import annotations

import textwrap
from typing import List

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from apps.node_man.models import GlobalSettings


class Command(BaseCommand):
    help = "Migrate incremental data for specific physical tables from one database to another."

    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.formatter_class = lambda prog: __import__('argparse').RawDescriptionHelpFormatter(prog)
        parser.description = textwrap.dedent("""
            Management command: migrate_incremental_tables

            This command migrates incremental data for a set of physical tables
            from one Django database alias to another, based on an id offset.

            Usage examples:

                # Migrate all supported tables from `default` to `target` where id > 100000
                ./manage.py migrate_incremental_tables \\
                    --source-db default \\
                    --target-db target \\
                    --offset 100000 

                # Only migrate subscription related tables
                ./manage.py migrate_incremental_tables \\
                    --source-db default \\
                    --target-db target \\
                    --offset 100000 \\
                    --tables node_man_subscription node_man_subscriptiontask

                # Dry-run, only print what would be inserted
                ./manage.py migrate_incremental_tables \\
                    --source-db default \\
                    --target-db target \\
                    --offset 100000 \\
                    --dry-run
            """)
        return parser

    # Default tables to migrate (in dependency-friendly order)
    DEFAULT_TABLES: List[str] = [
        "django_migrations",
        # "node_man_accesspoint",
        # "node_man_cloud",
        # "node_man_globalsettings",
        "node_man_gseconfigenv",
        "node_man_gseconfigextraenv",
        "node_man_gseconfigtemplate",
        "node_man_gseplugindesc",
        # "node_man_host",
        "node_man_installchannel",
        "node_man_packages",
        # NOTE:
        # `node_man_pipelinetree` is intentionally NOT included here.
        # Pipeline tree data will be migrated indirectly when processing
        # tables that reference it via a `pipeline_id` column.
        "node_man_pluginconfiginstance",
        "node_man_pluginconfigtemplate",
        "node_man_pluginresourcepolicy",
        "node_man_proccontrol",
        "node_man_processstatus",
        "node_man_subscription",
        "node_man_subscriptioninstancerecord",
        "node_man_subscriptionstep",
        "node_man_subscriptiontask",
        "tag_tag",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-db",
            dest="source_db",
            default="default",
            help='Source database alias to read data from (default: "default").',
        )
        parser.add_argument(
            "--target-db",
            dest="target_db",
            required=True,
            help="Target database alias to write data into.",
        )
        parser.add_argument(
            "--offset",
            dest="offset",
            type=int,
            default=None,
            help=(
                "Global id offset. For tables with an `id` column, rows with id > offset will be migrated. "
                "If omitted, per-table offsets will be loaded from GlobalSettings key `MIGRATE_OFFSET`."
            ),
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=1000,
            help="Batch size for incremental SELECT and INSERT (default: 1000).",
        )
        parser.add_argument(
            "--tables",
            nargs="*",
            dest="tables",
            help=(
                "Optional subset of table names to migrate. "
                "If omitted, a predefined list of tables will be migrated."
            ),
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Do not write anything to the target database, only log what would be migrated.",
        )

    def handle(self, *args, **options):
        source_db = options["source_db"]
        target_db = options["target_db"]
        offset = options["offset"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        if source_db not in connections.databases:
            raise CommandError(f"Source database alias `{source_db}` is not configured in DATABASES.")
        if target_db not in connections.databases:
            raise CommandError(f"Target database alias `{target_db}` is not configured in DATABASES.")
        if source_db == target_db:
            raise CommandError("source-db and target-db must be different.")

        # When offset is not provided, load per-table offsets from GlobalSettings.MIGRATE_OFFSET.
        use_migrate_offset_config = offset is None
        offsets_by_table = {}
        if use_migrate_offset_config:
            try:
                # 从“目标库”的 GlobalSettings 表读取 MIGRATE_OFFSET
                migrate_offset_obj = (
                    GlobalSettings.objects.using(target_db)
                    .filter(key="MIGRATE_OFFSET")
                    .only("v_json")
                    .first()
                )
                migrate_offset_conf = (migrate_offset_obj.v_json if migrate_offset_obj else {}) or {}
            except Exception as exc:
                print(
                    "Failed to load MIGRATE_OFFSET from GlobalSettings, fallback to empty dict: %s",
                    exc,
                )
                migrate_offset_conf = {}
            if not isinstance(migrate_offset_conf, dict):
                print(
                    "GlobalSettings MIGRATE_OFFSET is not a dict, got %r, fallback to empty dict.",
                    migrate_offset_conf,
                )
                migrate_offset_conf = {}
            for table_name, table_offset in migrate_offset_conf.items():
                try:
                    offsets_by_table[str(table_name)] = int(table_offset)
                except (TypeError, ValueError):
                    print(
                        "Invalid offset for table %s in MIGRATE_OFFSET: %r (ignored).",
                        table_name,
                        table_offset,
                    )

        # Determine which tables to migrate
        if options.get("tables"):
            requested_tables = options["tables"]
            unsupported = set(requested_tables) - set(self.DEFAULT_TABLES)
            if unsupported:
                raise CommandError(
                    "Unsupported table(s) requested: {}. Supported tables: {}".format(
                        ", ".join(sorted(unsupported)),
                        ", ".join(self.DEFAULT_TABLES),
                    )
                )
            tables = requested_tables
        else:
            tables = self.DEFAULT_TABLES

        print(
            f"Start incremental migration: source_db={source_db}, target_db={target_db}, "
            f"offset={'GLOBAL ' + str(offset) if not use_migrate_offset_config else 'GlobalSettings.MIGRATE_OFFSET'}, "
            f"batch_size={batch_size}, tables={tables}, dry_run={dry_run}",
        )

        total_migrated = 0
        # Initialize new_offsets_by_table with existing offsets so that tables without new
        # rows keep their previous offsets.
        new_offsets_by_table = dict(offsets_by_table) if use_migrate_offset_config else {}
        for table_name in tables:
            print(f"==== Migrate table `{table_name}` begin ====")
            try:
                if use_migrate_offset_config:
                    table_offset = offsets_by_table.get(table_name, 0)
                else:
                    table_offset = offset

                migrated_count, last_processed_id = self._migrate_single_table(
                    table_name=table_name,
                    source_alias=source_db,
                    target_alias=target_db,
                    offset=table_offset,
                    batch_size=batch_size,
                    dry_run=dry_run,
                )
            except Exception as exc:
                print("Migrate table `%s` failed: %s", table_name, exc)
                raise CommandError(f"Migrate table `{table_name}` failed: {exc}")

            total_migrated += migrated_count

            if use_migrate_offset_config and last_processed_id is not None:
                new_offsets_by_table[table_name] = last_processed_id

            print(
                f"==== Migrate table `{table_name}` done, migrated_rows={migrated_count}, "
                f"last_processed_id={last_processed_id} ===="
            )

        msg = (
            f"Incremental migration finished: source_db={source_db}, "
            f"target_db={target_db}, total_migrated_rows={total_migrated}, dry_run={dry_run}"
        )
        print(msg)
        self.stdout.write(self.style.SUCCESS(msg))

        # Persist updated per-table offsets back to GlobalSettings when we are
        # using MIGRATE_OFFSET and not running in dry-run mode.
        if use_migrate_offset_config and not dry_run:
            try:
                # 把 MIGRATE_OFFSET 写回到“目标库”的 GlobalSettings 表
                GlobalSettings.objects.using(target_db).update_or_create(
                    key="MIGRATE_OFFSET",
                    defaults={"v_json": new_offsets_by_table},
                )
                print(f"Updated GlobalSettings MIGRATE_OFFSET to: {new_offsets_by_table}")
            except Exception as exc:
                print("Failed to update MIGRATE_OFFSET in GlobalSettings: %s", exc)

    def _migrate_single_table(
        self,
        table_name: str,
        source_alias: str,
        target_alias: str,
        offset: int,
        batch_size: int,
        dry_run: bool,
    ) -> tuple:
        """
        Migrate data for one physical table.

        - For tables with an `id` column: migrate rows where id > offset, in ascending id order.
        - For tables without an `id` column: migrate all rows once (id-agnostic),
          relying on INSERT IGNORE / ON CONFLICT DO NOTHING for idempotency.

        Returns:
            (migrated_rows, last_processed_id)
            - migrated_rows: number of rows inserted into the target table.
            - last_processed_id: max id processed for this table (or None if the table
              has no `id` column or no rows were migrated).
        """
        # Special rule: `node_man_pipelinetree` must NOT be migrated as a standalone table.
        # It is migrated indirectly when processing tables that contain a `pipeline_id` column.
        if table_name == "node_man_pipelinetree":
            print(
                "Skip direct migration of `node_man_pipelinetree`: it will be migrated "
                "indirectly based on `pipeline_id` references from other tables."
            )
            return 0, None

        source_conn = connections[source_alias]
        target_conn = connections[target_alias]

        # Probe table schema and columns
        with source_conn.cursor() as src_cursor:
            src_cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
            description = src_cursor.description

        if not description:
            print("Table `%s` has no columns (empty description), skip.", table_name)
            return 0, None

        columns = [col[0] for col in description]
        has_id_column = "id" in columns
        id_index = columns.index("id") if has_id_column else None

        # Detect whether this table has a `pipeline_id` column; if so, we will
        # migrate related records from `node_man_pipelinetree` on the fly.
        has_pipeline_id_column = "pipeline_id" in columns
        pipeline_id_index = columns.index("pipeline_id") if has_pipeline_id_column else None

        print(
            f"Table `{table_name}` columns={columns}, "
            f"has_id_column={has_id_column}, has_pipeline_id_column={has_pipeline_id_column}",
        )

        # Build INSERT SQL template for the target database vendor
        column_list = ", ".join(f"`{col}`" for col in columns)
        placeholders = ", ".join(["%s"] * len(columns))

        vendor = target_conn.vendor
        if vendor == "mysql":
            insert_sql = f"INSERT IGNORE INTO {table_name} ({column_list}) VALUES ({placeholders})"
        elif vendor == "postgresql":
            insert_sql = (
                f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            )
        else:
            # Fallback: no special conflict handling, errors will bubble up
            insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

        total_inserted = 0
        max_processed_id = None

        if has_id_column:
            # Incremental by id: paginate by id > last_id
            last_id = offset
            while True:
                with source_conn.cursor() as src_cursor:
                    src_cursor.execute(
                        f"SELECT * FROM {table_name} WHERE id > %s ORDER BY id ASC LIMIT %s",
                        [last_id, batch_size],
                    )
                    rows = src_cursor.fetchall()

                if not rows:
                    break

                batch_size_actual = len(rows)
                max_id_in_batch = max(row[id_index] for row in rows)

                # Collect pipeline_ids from this batch if the column exists
                pipeline_ids_batch = []
                if has_pipeline_id_column:
                    pipeline_ids_batch = [
                        row[pipeline_id_index]
                        for row in rows
                        if row[pipeline_id_index]
                    ]

                if dry_run:
                    print(
                        f"Dry-run: table `{table_name}` would insert {batch_size_actual} "
                        f"rows (id in ({last_id}, {max_id_in_batch}]]."
                    )
                else:
                    with transaction.atomic(using=target_alias):
                        with target_conn.cursor() as dest_cursor:
                            dest_cursor.executemany(insert_sql, rows)

                    print(
                        f"Inserted {batch_size_actual} rows into `{table_name}` "
                        f"(id in ({last_id}, {max_id_in_batch}]]."
                    )

                # For tables with a `pipeline_id` column, migrate related pipeline trees
                if pipeline_ids_batch and has_pipeline_id_column:
                    self._migrate_pipeline_trees_for_ids(
                        pipeline_ids=pipeline_ids_batch,
                        source_alias=source_alias,
                        target_alias=target_alias,
                        dry_run=dry_run,
                    )

                total_inserted += batch_size_actual
                last_id = max_id_in_batch
                max_processed_id = max_id_in_batch
        else:
            # No id column: migrate all rows in one shot (usually small tables)
            with source_conn.cursor() as src_cursor:
                src_cursor.execute(f"SELECT * FROM {table_name}")
                rows = src_cursor.fetchall()

            if not rows:
                print(f"Table `{table_name}` has no rows to migrate.")
                return 0, None

            # Collect pipeline_ids for full-table copy if the column exists
            pipeline_ids_all = []
            if has_pipeline_id_column:
                pipeline_ids_all = [
                    row[pipeline_id_index]
                    for row in rows
                    if row[pipeline_id_index]
                ]

            if dry_run:
                print(
                    f"Dry-run: table `{table_name}` would insert {len(rows)} rows "
                    f"(no id column, full-table copy).",
                )
            else:
                with transaction.atomic(using=target_alias):
                    with target_conn.cursor() as dest_cursor:
                        dest_cursor.executemany(insert_sql, rows)

                print(
                    f"Inserted {len(rows)} rows into `{table_name}` "
                    f"(no id column, full-table copy).",
                )

            # For tables with a `pipeline_id` column, migrate related pipeline trees
            if pipeline_ids_all and has_pipeline_id_column:
                self._migrate_pipeline_trees_for_ids(
                    pipeline_ids=pipeline_ids_all,
                    source_alias=source_alias,
                    target_alias=target_alias,
                    dry_run=dry_run,
                )

            total_inserted = len(rows)

        return total_inserted, max_processed_id

    def _migrate_pipeline_trees_for_ids(
        self,
        pipeline_ids,
        source_alias: str,
        target_alias: str,
        dry_run: bool,
    ) -> int:
        """
        Migrate corresponding rows in `node_man_pipelinetree` for the given pipeline_ids.

        This helper is called when migrating any table that has a `pipeline_id` column.
        It ensures that the related pipeline trees are present in the target database.
        """
        # Normalize and deduplicate pipeline ids
        unique_ids = sorted({pid for pid in pipeline_ids if pid})
        if not unique_ids:
            return 0

        source_conn = connections[source_alias]
        target_conn = connections[target_alias]

        placeholders = ", ".join(["%s"] * len(unique_ids))
        select_sql = (
            f"SELECT id, tree FROM node_man_pipelinetree WHERE id IN ({placeholders})"
        )

        with source_conn.cursor() as src_cursor:
            src_cursor.execute(select_sql, unique_ids)
            rows = src_cursor.fetchall()

        if not rows:
            print(
                "No rows found in `node_man_pipelinetree` for pipeline_ids: "
                f"{unique_ids}"
            )
            return 0

        vendor = target_conn.vendor
        if vendor == "mysql":
            insert_sql = (
                "INSERT IGNORE INTO node_man_pipelinetree (`id`, `tree`) "
                "VALUES (%s, %s)"
            )
        elif vendor == "postgresql":
            # Explicitly specify conflict target for PostgreSQL
            insert_sql = (
                'INSERT INTO node_man_pipelinetree ("id", "tree") '
                "VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
            )
        else:
            insert_sql = (
                "INSERT INTO node_man_pipelinetree (id, tree) VALUES (%s, %s)"
            )

        if dry_run:
            print(
                "Dry-run: `node_man_pipelinetree` would insert "
                f"{len(rows)} rows for pipeline_ids: {unique_ids}."
            )
            return len(rows)

        with transaction.atomic(using=target_alias):
            with target_conn.cursor() as dest_cursor:
                dest_cursor.executemany(insert_sql, rows)

        print(
            f"Inserted {len(rows)} rows into `node_man_pipelinetree` "
        )
        return len(rows)