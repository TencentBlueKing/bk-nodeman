# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import csv
import json
import os
import typing
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from MySQLdb.connections import Connection

from apps.node_man import constants, models
from common.log import logger

ENV_OFFSET_TABLE = "cc_EnvIDOffset"
ENV_BIZ_MAP_TABLE = "cc_EnvBizMap"
PROXY_EXTRA_DATA = (
    '{"data_path": "/var/lib/gse_sg", "bt_speed_limit": "", '
    '"peer_exchange_switch_for_agent": 0, "enable_compression": false}'
)


class Command(BaseCommand):
    def add_arguments(self, parser):

        parser.add_argument(
            "--is_switch_env_ap",
            help="export another env info file path",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--is_migrate_proxy_info",
            help="export another env info file path",
            action="store_true",
            default=False,
        )
        parser.add_argument("--env_name", help="导出环境名称")
        parser.add_argument("--bk_biz_ids", help="当前环境中需要迁移的业务 ID 列表, 格式: '1,2,3'")
        parser.add_argument("--mysql_host", help="公共数据库地址")
        parser.add_argument("--mysql_port", help="公共数据库端口", default=3306)
        parser.add_argument("--mysql_user", help="公共数据库用户", default="root")
        parser.add_argument("--mysql_db", help="公共数据库链接库名称", default="sg_migration")
        parser.add_argument("--mysql_password", help="公共数据库密码")
        parser.add_argument("--env_offset_table", help="环境映射表", default=ENV_OFFSET_TABLE)
        parser.add_argument("--env_biz_map_table", help="业务映射表", default=ENV_BIZ_MAP_TABLE)
        parser.add_argument("--old_ap__new_ap_map", help="导出环境接入点与当前接入点映射关系, 格式: '1:2,2:3'")
        parser.add_argument("--cloud_file_path", help="导出环境管控区域信息文件路径", default="node_man_export/cloud_info.csv")
        parser.add_argument(
            "--proxy_file_path", help="导出环境 Proxy 主机信息文件路径", default="node_man_export/proxy_host_info.csv"
        )
        parser.add_argument("--proxy_extra_data", help="指定导入环境 Proxy 主机 extra 矫正信息", default=PROXY_EXTRA_DATA)

    def handle(self, *args, **options):
        env_name: str = options["env_name"]
        host: str = options["mysql_host"]
        port: int = options["mysql_port"]
        database: str = options["mysql_db"]
        username: str = options["mysql_user"]
        password: str = options["mysql_password"]
        env_offset_table: str = options["env_offset_table"]
        env_biz_map_table: str = options["env_biz_map_table"]
        old_ap__new_ap_map: str = options["old_ap__new_ap_map"]
        cloud_file_path: str = options["cloud_file_path"]
        proxy_info_file_path: str = options["proxy_file_path"]
        bk_biz_id_string: str = options["bk_biz_ids"]
        is_migration_proxy_info: bool = options["is_migrate_proxy_info"]
        is_switch_env_ap: bool = options["is_switch_env_ap"]
        position_proxy_extra_data: typing.Dict[str, typing.Any] = options["proxy_extra_data"]

        try:
            position_proxy_extra_data = json.loads(position_proxy_extra_data)
        except Exception as e:
            raise Exception(f"proxy_extra_data 格式错误: {e}")

        mysql_config: typing.Dict[str, typing.Union[int, str]] = {
            "host": host,
            "port": port,
            "user": username,
            "passwd": password,
            "db": database,
        }

        load_env_handler: LoadEnvHandler = LoadEnvHandler(env_name=env_name, ap_map=old_ap__new_ap_map)
        load_env_handler.load_env_info(
            mysql_config=mysql_config,
            env_offset_table=env_offset_table,
            env_biz_map_table=env_biz_map_table,
            is_migrate_proxy_info=is_migration_proxy_info,
            bk_biz_ids=bk_biz_id_string,
            is_switch_env_ap=is_switch_env_ap,
            proxy_info_file_path=proxy_info_file_path,
            cloud_info_file_path=cloud_file_path,
            position_proxy_extra_data=position_proxy_extra_data,
        )


class LoadEnvHandler(object):
    def __init__(self, env_name: str, ap_map: str):
        self.env_name = env_name
        self.ap_map = self.parse_ap_map(ap_map)

    def load_env_info(
        self,
        mysql_config: typing.Dict[str, str],
        position_proxy_extra_data: typing.Dict[str, typing.Any],
        env_offset_table: str,
        env_biz_map_table: str,
        is_migrate_proxy_info: bool,
        bk_biz_ids: str = None,
        is_switch_env_ap: bool = True,
        proxy_info_file_path=None,
        cloud_info_file_path=None,
    ):

        env_map = self.get_env_map(
            mysql_config=mysql_config, env_offset_table=env_offset_table, env_biz_map_table=env_biz_map_table
        )
        logger.info(f"Export and load env relationship: {env_map}")
        offset: int = env_map["offset"]
        bk_biz_ids: typing.List[int] = self.parse_biz_list(bk_biz_ids)
        with transaction.atomic():
            if is_migrate_proxy_info:
                self.position_proxy_host(
                    bk_biz_ids=bk_biz_ids,
                    proxy_info_file_path=proxy_info_file_path,
                    offset=offset,
                    bk_biz_map=env_map["bk_biz_map"],
                    position_proxy_extra_data=position_proxy_extra_data,
                )
            if is_switch_env_ap:
                self.switch_cloud_ap_id(ap_map=self.ap_map, cloud_info_file_path=cloud_info_file_path, offset=offset)
                self.switch_host_ap(
                    ap_map=self.ap_map, offset=offset, bk_biz_ids=bk_biz_ids, cloud_info_file_path=cloud_info_file_path
                )

    @classmethod
    def get_cloud_ap_map(cls, cloud_info_file_path: str) -> typing.Dict[int, int]:
        """
        获取导出环境内的管控区域与接入点映射关系
        """
        cloud_reader = cls.check_and_read_csv_file(cloud_info_file_path)
        old_cloud_id__ap_id_map: typing.Dict[int, int] = {
            old_cloud["bk_cloud_id"]: old_cloud["ap_id"] for old_cloud in cloud_reader
        }
        return old_cloud_id__ap_id_map

    @classmethod
    def get_proxy_host_info(cls, proxy_info_file_path: str):
        """
        获取导出环境内的 Proxy 主机信息
        """
        host_id__proxy_info_map: typing.Dict[int, typing.Dict[str, str]] = defaultdict(int)
        old_biz_id__host_ids: typing.Dict[int, typing.List[int]] = defaultdict(list)

        proxy_csv_reader = cls.check_and_read_csv_file(proxy_info_file_path)
        for proxy_host_info in proxy_csv_reader:
            old_biz_id__host_ids[proxy_host_info["bk_biz_id"]].append(proxy_host_info["bk_host_id"])
            host_id__proxy_info_map[proxy_host_info["bk_host_id"]] = proxy_host_info

        return old_biz_id__host_ids, host_id__proxy_info_map

    @classmethod
    def switch_cloud_ap_id(cls, ap_map: typing.Dict[int, int], cloud_info_file_path: str, offset: int):
        """
        通过管控区域名称和接入点映射 矫正当前管控区域的接入点
        """
        # 校验接入点映射关系的新接入点是否存在于当前环境
        current_ap_ids: typing.List[int] = models.AccessPoint.objects.values_list("id", flat=True)
        not_in_current_ap_ids: typing.List[int] = [ap_id for ap_id in ap_map.values() if ap_id not in current_ap_ids]

        if constants.DEFAULT_AP_ID in not_in_current_ap_ids:
            logger.warning(
                f"AccessPoint [{constants.DEFAULT_AP_ID}] not exist in the current environment, the access point "
                f"belongs to the automatic selection access point, does not need to exist"
            )
            not_in_current_ap_ids.remove(constants.DEFAULT_AP_ID)
        if not_in_current_ap_ids:
            raise Exception(f"接入点{not_in_current_ap_ids}不存在于当前环境, 请检查接入点映射关系是否正确")
        old_cloud_id__ap_id_map: typing.Dict[int, int] = cls.get_cloud_ap_map(cloud_info_file_path)

        current_cloud_ids: typing.List[int] = models.Cloud.objects.values_list("bk_cloud_id", flat=True)
        complete_switch_cloud_ids: typing.List[int] = []
        for old_cloud_id, old_ap_id in old_cloud_id__ap_id_map.items():
            new_cloud_id: int = old_cloud_id + offset
            try:
                new_ap_id: int = ap_map[old_ap_id]
            except KeyError:
                raise Exception(
                    f"Export env access point [{old_ap_id}] does not exist in the access point mapping relationship, "
                    f"please check whether the access point mapping relationship -> [{ap_map}] is correct"
                )
            if new_cloud_id not in current_cloud_ids:
                logger.error(f"管控区域{new_cloud_id}不存在于当前环境, 请检查是否正确同步管控区域信息")
            else:
                logger.info(f"开始切换管控区域{new_cloud_id}的接入点为{new_ap_id}")
                models.Cloud.objects.filter(bk_cloud_id=new_cloud_id).update(ap_id=new_ap_id)
                complete_switch_cloud_ids.append(new_cloud_id)

        logger.info(
            f"当前环境下管控区域 ID 为 -> {complete_switch_cloud_ids} 的管控区域接入点切换完成, 总体切换管控区域数量为 -> "
            f"{len(complete_switch_cloud_ids)}"
        )

    def position_proxy_host(
        self,
        bk_biz_ids: typing.List[int],
        proxy_info_file_path: str,
        offset: int,
        bk_biz_map: typing.Dict[int, int],
        position_proxy_extra_data: typing.Dict[str, typing.Any],
    ):
        """
        通过主机 ID 偏移量，定位当前环境内的 Proxy 主机
        """
        old_biz_id__host_ids, host_id__proxy_info_map = self.get_proxy_host_info(proxy_info_file_path)

        without_proxy_biz_ids: typing.List[int] = [
            biz_id for biz_id in bk_biz_ids if bk_biz_map[biz_id] not in old_biz_id__host_ids.keys()
        ]

        for new_biz_id in without_proxy_biz_ids:
            logger.error(f"新业务 ID -> [{new_biz_id}] 对应的导出环境业务 ID -> [{bk_biz_map[new_biz_id]}] 没有 Proxy 主机")

        bk_biz_ids: typing.List[int] = [biz_id for biz_id in bk_biz_ids if biz_id not in without_proxy_biz_ids]

        new_env_host_ids: typing.List[int] = models.Host.objects.filter(bk_biz_id__in=bk_biz_ids).values_list(
            "bk_host_id", flat=True
        )
        total_position_host_ids: typing.List[int] = []
        for new_biz_id in bk_biz_ids:
            old_biz_id: int = bk_biz_map[new_biz_id]
            for old_host_id in old_biz_id__host_ids[old_biz_id]:
                total_position_host_ids.append(old_host_id + offset)

        not_in_env_host_ids: typing.List[int] = []
        for new_host_id in total_position_host_ids:
            if new_host_id not in new_env_host_ids:
                total_position_host_ids.remove(new_host_id)
                not_in_env_host_ids.append(new_host_id)
        if not_in_env_host_ids:
            logger.error(f"主机 ID 为 {not_in_env_host_ids} 的主机不存在于当前业务 -> {bk_biz_ids} 内, 请检查主机 ID 偏移量是否正确")

        logger.info(f"开始将业务ID -> [{bk_biz_ids}] 下的主机 -> [{total_position_host_ids}] 转换主机类型为 Proxy")
        models.Host.objects.filter(bk_host_id__in=total_position_host_ids, bk_biz_id__in=bk_biz_ids).update(
            node_type=constants.NodeType.PROXY
        )
        logger.info(f"业务 -> [{bk_biz_ids}] 下主机 ID 为 -> [{total_position_host_ids}] 的主机转换类型为 Proxy 完成")

        logger.info(f"开始将主机 -> [{total_position_host_ids}] 数据矫正，包括 login_ip 和 extra_data")
        for new_host_id in total_position_host_ids:
            old_host_id: int = new_host_id - offset
            host_info: typing.Dict[int, typing.Any] = host_id__proxy_info_map[old_host_id]
            login_ip: typing.Optional[str] = host_info.get("login_ip") or host_info.get("outer_ip")
            if not login_ip:
                logger.info(f"主机 ID -> [{new_host_id}] 不存在对应的 login_ip or outer_ip, 放弃矫正 IP 数据")
                continue
            else:
                models.Host.objects.filter(bk_host_id=new_host_id, bk_biz_id__in=bk_biz_ids).update(login_ip=login_ip)

        models.Host.objects.filter(bk_host_id__in=total_position_host_ids, bk_biz_id__in=bk_biz_ids).update(
            extra_data=position_proxy_extra_data
        )

    def switch_host_ap(
        self,
        bk_biz_ids: typing.List[int],
        ap_map: typing.Dict[int, int],
        cloud_info_file_path: str,
        offset: int,
    ):
        """
        通过接入点映射关系，切换当前环境内管控区域的所有主机接入点
        """
        # 直连区域 Agent 不需要处理
        old_cloud_id__ap_id_map: typing.Dict[int, int] = self.get_cloud_ap_map(
            cloud_info_file_path=cloud_info_file_path
        )

        new_cloud_id__ap_id_map: typing.Dict[int, int] = {}
        for old_cloud_id, old_ap_id in old_cloud_id__ap_id_map.items():
            new_cloud_id: int = old_cloud_id + offset
            new_ap_id: int = ap_map[old_ap_id]
            new_cloud_id__ap_id_map[new_cloud_id] = new_ap_id

        for new_cloud_id, new_ap_id in new_cloud_id__ap_id_map.items():
            logger.info(f"开始切换管控区域 -> {new_cloud_id} & 业务 -> [{bk_biz_ids}]下的主机接入点为{new_ap_id}")
            models.Host.objects.filter(bk_cloud_id=new_cloud_id, bk_biz_id__in=bk_biz_ids).update(ap_id=new_ap_id)

        logger.info(f"业务 -> [{bk_biz_ids}] 内并且位于管控区域 ID -> [{new_cloud_id__ap_id_map.keys()}] 下的主机接入点切换完成")

    @classmethod
    def check_and_read_csv_file(cls, csv_file_path: str):
        """
        检查导入文件格式并且读取文件
        """
        if not os.path.isfile(csv_file_path):
            raise Exception(f"预导入数据文件 '{csv_file_path}' does not exist")

        read_lines = []
        with open(csv_file_path, "r") as csv_file:
            try:
                dialect = csv.Sniffer().sniff(csv_file.read(1024))
                csv_file.seek(0)
                csv_reader = csv.DictReader(csv_file, dialect=dialect)
            except csv.Error:
                raise Exception(f"预导入数据文件 '{csv_file_path}' is not a valid CSV file")

            for row in csv_reader:
                int_value_row = {}
                for key, value in row.items():
                    try:
                        int_value = int(value)
                        int_value_row[key] = int_value
                    except ValueError:
                        int_value_row[key] = value
                read_lines.append(int_value_row)

        return read_lines

    @classmethod
    def parse_ap_map(cls, map_string: str) -> typing.Dict[int, int]:
        """
        解析接入点映射关系，格式为 1-2,4-3 , 1 代表当前接入点，2 代表导入环境接入点 ID
        """
        ap_map: typing.Dict[int, int] = {}

        for item in map_string.split(","):
            try:
                new_ap, old_ap = item.split(":")
                ap_map[int(new_ap)] = int(old_ap)
            except ValueError as e:
                raise ValueError(f"解析接入点映射关系失败 -> {e}")

        return ap_map

    @classmethod
    def parse_biz_list(cls, biz_string: str) -> typing.List[int]:
        """
        解析业务 ID 列表，格式为 1,2,3
        """
        biz_list: typing.List[int] = []

        for item in biz_string.split(","):
            try:
                biz_list.append(int(item))
            except ValueError as e:
                raise ValueError(f"解析业务 ID 列表失败 -> {e}")

        return biz_list

    def get_env_map(
        self, mysql_config, env_offset_table, env_biz_map_table
    ) -> typing.Dict[str, typing.Union[int, typing.Dict[int, int]]]:

        if hasattr(self, "env_map") and getattr(self, "env_map"):
            return self.env_map
        else:
            for config_field, config_value in mysql_config.items():
                if not config_value:
                    raise Exception(f"MySQL 配置项 -> [{config_field}] 值为空")
                if config_field != "port":
                    mysql_config[config_field] = str(config_value)
                else:
                    mysql_config[config_field] = int(config_value)
            conn: Connection = Connection(**mysql_config)
            cursor = conn.cursor()

            cursor.execute("select env, offset from {}".format(env_offset_table))
            env_offset_info = cursor.fetchall()

            cursor.execute(
                "select bk_old_biz_name, bk_old_biz_id, bk_new_biz_name, bk_new_biz_id, bk_env from {}".format(
                    env_biz_map_table
                )
            )
            env_biz_map_info = cursor.fetchall()

            env_biz_map_list = []
            for env_biz in env_biz_map_info:
                env_biz_map_list.append(
                    {
                        "bk_old_biz_name": env_biz[0],
                        "bk_old_biz_id": env_biz[1],
                        "bk_new_biz_name": env_biz[2],
                        "bk_new_biz_id": env_biz[3],
                        "bk_env": env_biz[4],
                    }
                )

            env_offset_map_list = []
            for env_offset in env_offset_info:
                env_offset_map_list.append({"env": env_offset[0], "offset": env_offset[1]})

            cursor.close()
            conn.close()
            env_map = {
                "ap_map": self.ap_map,
                "offset": self.get_env_offset(env_offset_map_list),
                "bk_biz_map": self.get_env_biz_map(env_biz_map_list),
            }
            setattr(self, "env_map", env_map)
            return env_map

    def get_env_offset(self, env_offset_map_list) -> int:
        # 如果env 不存在与 env_offset_map_list 中则抛出异常
        if self.env_name not in [env_map["env"] for env_map in env_offset_map_list]:
            raise Exception(f"环境 {self.env_name} 不存在于环境映射关系表 -> {env_offset_map_list}")

        for env_info in env_offset_map_list:
            if env_info["env"] == self.env_name:
                return env_info["offset"]

    def get_env_biz_map(self, env_biz_map_list) -> typing.Dict[int, int]:
        # 如果env 不存在与 env_biz_map_list 中则抛出异常
        if self.env_name not in [env_biz_map["bk_env"] for env_biz_map in env_biz_map_list]:
            raise Exception(f"环境 {self.env_name} 不存在于环境业务映射关系表 -> {env_biz_map_list}")

        bk_biz_map: typing.Dict[int, int] = {}
        for env_biz_map_info in env_biz_map_list:
            if env_biz_map_info["bk_env"] == self.env_name:
                try:
                    bk_biz_map[env_biz_map_info["bk_new_biz_id"]] = env_biz_map_info["bk_old_biz_id"]
                except Exception as e:
                    raise Exception(f"通过拉取的业务映射关系表获取业务映射关系失败 -> error: {e}")

        return bk_biz_map
