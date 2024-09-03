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
import typing
from collections import defaultdict
from ipaddress import IPv4Address

from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.backend.subscription.steps.agent_adapter.adapter import (
    LEGACY,
    AgentVersionSerializer,
)
from apps.core.gray.constants import INSTALL_OTHER_AGENT_AP_ID_OFFSET
from apps.core.gray.handlers import GrayHandler
from apps.core.gray.tools import GrayTools
from apps.core.ipchooser.tools.base import HostQuerySqlHelper
from apps.exceptions import ApiError, ValidationError
from apps.node_man import constants, models, tools
from apps.node_man.handlers import validator
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.periodic_tasks.sync_cmdb_host import bulk_differential_sync_biz_hosts
from apps.utils import basic
from env.constants import GseVersion


def set_agent_setup_info_to_attrs(attrs):
    """
    注入 Agent 安装配置信息
    :param attrs:
    :return:
    """
    # # 如果开启业务灰度，安装新版本 Agent
    # name = ("gse_agent", "gse_proxy")[attrs["node_type"] == "PROXY"]
    # # TODO 后续该逻辑通过前端表单填写，通过 validate 校验是否属于灰度范围（暂时只支持到业务级别）
    # visible_range_handler = VisibleRangeHandler(
    #     name=name, version_str="test", target_type=core_tag_constants.TargetType.AGENT.value
    # )
    # if all([visible_range_handler.is_belong_to_biz(bk_biz_id) for bk_biz_id in bk_biz_ids]):
    #     attrs["agent_setup_info"] = {"name": name, "version": "test"}

    if not settings.BKAPP_ENABLE_DHCP:
        return

    # 如果开启 DHCP，安装 2.0 Agent，开启 AgentID 特性
    # 在执行模块根据主机接入点所属的 GSE 版本决定是否采用下列的 agent_setup_info
    name = ("gse_agent", "gse_proxy")[attrs["node_type"] == "PROXY"]
    # attrs["agent_setup_info"]["name"] = name
    # 处理重装类型setup_info结构
    agent_setup_info = attrs.get("agent_setup_info", {})
    global_settings_agent_version = models.GlobalSettings.get_config(
        models.GlobalSettings.KeyEnum.GSE_AGENT2_VERSION.value, default="stable"
    )

    attrs["agent_setup_info"] = {
        "name": name,
        "version": agent_setup_info.get("version") or global_settings_agent_version,
        "choice_version_type": agent_setup_info.get("choice_version_type") or constants.AgentVersionType.UNIFIED.value,
        "version_map_list": agent_setup_info.get("version_map_list", []),
    }


class SortSerializer(serializers.Serializer):
    head = serializers.ChoiceField(label=_("排序字段"), choices=list(constants.HEAD_TUPLE))
    sort_type = serializers.ChoiceField(label=_("排序类型"), choices=list(constants.SORT_TUPLE))


class ListSerializer(serializers.Serializer):
    job_id = serializers.ListField(label=_("任务ID"), required=False)
    status = serializers.ListField(label=_("状态"), required=False)
    created_by = serializers.ListField(label=_("执行者"), required=False)
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    inner_ip_list = serializers.ListField(label=_("搜索IP"), required=False)
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    sort = SortSerializer(label=_("排序"), required=False)
    hide_auto_trigger_job = serializers.BooleanField(label=_("隐藏自动部署任务"), required=False, default=False)

    step_type = serializers.ListField(label=_("任务类型列表"), required=False)
    op_type = serializers.ListField(label=_("操作类型列表"), required=False)
    policy_name = serializers.ListField(label=_("策略名称列表"), child=serializers.CharField(), required=False)

    # 时间范围
    start_time = serializers.DateTimeField(label=_("起始时间"), required=False)
    end_time = serializers.DateTimeField(label=_("终止时间"), required=False)


class InstallBaseSerializer(serializers.Serializer):

    op_not_need_identity = [
        constants.OpType.REINSTALL,
        constants.OpType.RESTART,
        constants.OpType.UPGRADE,
        constants.OpType.UNINSTALL,
        constants.OpType.RELOAD,
    ]

    def backfill_bk_host_id(self, hosts):
        query_params = Q()
        query_params.connector = "OR"
        cloud_ip_host_info_map = {}
        need_backfill_host_id: bool = False
        for _host in hosts:
            if _host.get("bk_host_id") is None:
                # 任一台主机没有 bk_host_id，视为需要回填
                need_backfill_host_id = True
                sub_query = Q()
                sub_query.connector = "AND"
                sub_query.children.append(("bk_cloud_id", _host["bk_cloud_id"]))
                if _host.get("inner_ip"):
                    sub_query.children.append(("inner_ip", _host["inner_ip"]))
                    ip_key = _host["inner_ip"]
                else:
                    sub_query.children.append(("inner_ipv6", _host["inner_ipv6"]))
                    ip_key = _host["inner_ipv6"]
                cloud_ip_host_info_map[f"{_host['bk_cloud_id']}:{ip_key}"] = _host
                query_params.children.append(sub_query)

        # 如果不需要回填 HostID，直接返回，减少性能损耗
        if not need_backfill_host_id:
            return

        query_hosts: typing.List[typing.Dict] = models.Host.objects.filter(query_params).values(
            "bk_host_id", "bk_cloud_id", "inner_ip", "inner_ipv6"
        )

        cloup_ip_host_id_map = {}
        for _query_host in query_hosts:
            if _query_host["inner_ip"]:
                cloup_ip_host_id_map[f"{_query_host['bk_cloud_id']}:{_query_host['inner_ip']}"] = _query_host[
                    "bk_host_id"
                ]
            if _query_host["inner_ipv6"]:
                cloup_ip_host_id_map[f"{_query_host['bk_cloud_id']}:{_query_host['inner_ipv6']}"] = _query_host[
                    "bk_host_id"
                ]

        for cloud_ip, host_info in cloud_ip_host_info_map.items():
            host_info["bk_host_id"] = cloup_ip_host_id_map[cloud_ip]

    def backfill_ap_id(self, hosts):
        use_ap_map_host_ids: typing.List[int] = [host["bk_host_id"] for host in hosts if host["is_use_ap_map"]]
        if use_ap_map_host_ids:
            gray_ap_map: typing.Dict[int, int] = GrayHandler.get_gray_ap_map()
            host_queryset = models.Host.objects.filter(bk_host_id__in=use_ap_map_host_ids).values("bk_host_id", "ap_id")
            host_id_ap_map: typing.Dict[int, int] = {_host["bk_host_id"]: _host["ap_id"] for _host in host_queryset}
            for host in hosts:
                if not host["is_use_ap_map"]:
                    continue

                try:
                    host["ap_id"] = gray_ap_map[host_id_ap_map[host["bk_host_id"]]]
                except KeyError:
                    raise ValidationError(
                        _("缺少与主机ID: {bk_host_id} AP ID: {ap_id} 对应的接入点映射，请联系管理员配置").format(
                            bk_host_id=host["bk_host_id"], ap_id=host_id_ap_map[host["bk_host_id"]]
                        )
                    )


class HostSerializer(InstallBaseSerializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"))
    bk_cloud_id = serializers.IntegerField(label=_("管控区域ID"))
    bk_host_id = serializers.IntegerField(label=_("主机ID"), required=False)
    bk_addressing = serializers.ChoiceField(
        label=_("寻址方式"),
        choices=constants.CmdbAddressingType.list_member_values(),
        required=False,
        default=constants.CmdbAddressingType.STATIC.value,
    )
    ap_id = serializers.IntegerField(label=_("接入点ID"), required=False)
    install_channel_id = serializers.IntegerField(label=_("安装通道ID"), required=False, allow_null=True)
    inner_ip = serializers.IPAddressField(label=_("内网IP"), required=False, allow_blank=True, protocol="ipv4")
    outer_ip = serializers.CharField(label=_("外网IP"), required=False, allow_blank=True)
    login_ip = serializers.IPAddressField(label=_("登录IP"), required=False, allow_blank=True, protocol="both")
    data_ip = serializers.IPAddressField(label=_("数据IP"), required=False, allow_blank=True, protocol="both")
    inner_ipv6 = serializers.IPAddressField(label=_("内网IPv6"), required=False, allow_blank=True, protocol="ipv6")
    outer_ipv6 = serializers.IPAddressField(label=_("外网IPv6"), required=False, allow_blank=True, protocol="ipv6")

    os_type = serializers.ChoiceField(label=_("操作系统"), choices=list(constants.OS_TUPLE))
    auth_type = serializers.ChoiceField(label=_("认证类型"), choices=list(constants.AUTH_TUPLE), required=False)
    account = serializers.CharField(label=_("账户"), required=False, allow_blank=True)
    password = serializers.CharField(label=_("密码"), required=False, allow_blank=True)
    port = serializers.IntegerField(label=_("端口"), required=False)
    key = serializers.CharField(label=_("密钥"), required=False, allow_blank=True)
    is_manual = serializers.BooleanField(label=_("是否手动模式"), required=False, default=False)
    retention = serializers.IntegerField(label=_("密码保留天数"), required=False)
    peer_exchange_switch_for_agent = serializers.IntegerField(label=_("加速设置"), required=False, default=0)
    bt_speed_limit = serializers.IntegerField(label=_("传输限速"), required=False)
    data_path = serializers.CharField(label=_("数据文件路径"), required=False, allow_blank=True)
    is_need_inject_ap_id = serializers.BooleanField(label=_("是否需要注入ap_id到meta"), required=False, default=False)
    enable_compression = serializers.BooleanField(label=_("数据压缩开关"), required=False, default=False)
    is_use_ap_map = serializers.BooleanField(label=_("是否使用映射接入点"), required=False, default=False)
    force_update_agent_id = serializers.BooleanField(label=_("是否更新agent_id"), required=False, default=False)

    def validate(self, attrs):
        # 获取任务类型，如果是除安装以外的操作，则密码和秘钥可以为空
        job_type = self.root.initial_data.get("job_type", "")
        op_type = job_type.split("_")[0]
        node_type = job_type.split("_")[1]

        if not (attrs.get("inner_ip") or attrs.get("inner_ipv6")):
            raise ValidationError(_("请求参数 inner_ip 和 inner_ipv6 不能同时为空"))
        if node_type == constants.NodeType.PROXY and not (attrs.get("outer_ip") or attrs.get("outer_ipv6")):
            raise ValidationError(_("Proxy 操作的请求参数 outer_ip 和 outer_ipv6 不能同时为空"))
        if not attrs.get("outer_ipv6") and attrs.get("outer_ip"):
            outer_ips = attrs["outer_ip"].split(",")
            try:
                [IPv4Address(outer_ip) for outer_ip in outer_ips]
            except ValueError:
                raise ValidationError(_("Proxy 操作的请求参数 outer_ip:请输入一个合法的IPv4地址"))

        basic.ipv6_formatter(data=attrs, ipv6_field_names=["inner_ipv6", "outer_ipv6", "login_ip", "data_ip"])

        if attrs["is_use_ap_map"]:
            attrs["is_need_inject_ap_id"] = True

        if (
            not attrs.get("is_manual")
            and not attrs.get("auth_type")
            and job_type not in [constants.JobType.RELOAD_AGENT, constants.JobType.RELOAD_PROXY]
        ):
            raise ValidationError(_("{op_type} 操作必须填写认证类型").format(op_type=op_type))

        if op_type in self.op_not_need_identity:
            if all(
                [
                    attrs.get("bk_host_id") is None,
                    all(
                        [
                            attrs.get("bk_cloud_id") is None,
                            attrs.get("inner_ip") is None or attrs.get("inner_ipv6") is None,
                        ]
                    ),
                ]
            ):
                raise ValidationError(_("bk_host_id 或者 管控区域加IP组合必须选择一种"))

        # identity校验
        if op_type not in self.op_not_need_identity and not attrs.get("is_manual"):
            if not attrs.get("password") and attrs["auth_type"] == constants.AuthType.PASSWORD:
                raise ValidationError(_("密码认证方式必须填写密码"))
            if not attrs.get("key") and attrs["auth_type"] == constants.AuthType.KEY:
                raise ValidationError(_("密钥认证方式必须上传密钥"))
            if attrs.get("account") is None or attrs.get("port") is None:
                raise ValidationError(_("必须上传账号和端口"))

        # 直连区域必须填写Ap_id
        ap_id = attrs.get("ap_id")
        if attrs["bk_cloud_id"] == int(constants.DEFAULT_CLOUD) and ap_id is None and not attrs["is_use_ap_map"]:
            raise ValidationError(_("直连区域必须填写Ap_id或使用映射"))

        # 去除空值
        if attrs.get("key") == "":
            attrs.pop("key")
        if attrs.get("password") == "":
            attrs.pop("password")

        return attrs


class AgentSetupInfoSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, label="构件名称")
    # LEGACY 表示旧版本 Agent，仅做兼容
    version = serializers.CharField(required=False, label="构件版本", default=LEGACY)

    choice_version_type = serializers.ChoiceField(
        required=False, choices=constants.AgentVersionType.list_choices(), label=_("选择Agent Version类型")
    )
    version_map_list = AgentVersionSerializer(required=False, many=True)


class ScriptHook(serializers.Serializer):
    name = serializers.CharField(label=_("脚本名称"), min_length=1)


class InstallSerializer(InstallBaseSerializer):
    agent_setup_info = AgentSetupInfoSerializer(label=_("Agent 设置信息"), required=False)
    job_type = serializers.ChoiceField(label=_("任务类型"), choices=list(constants.JOB_TYPE_DICT))
    hosts = HostSerializer(label=_("主机信息"), many=True)
    replace_host_id = serializers.IntegerField(label=_("被替换的Proxy主机ID"), required=False)
    is_install_latest_plugins = serializers.BooleanField(label=_("是否安装最新版本插件"), required=False, default=True)
    is_install_other_agent = serializers.BooleanField(label=_("是否为安装额外Agent"), required=False, default=False)
    script_hooks = serializers.ListField(
        label=_("脚本钩子列表"),
        required=False,
        child=ScriptHook(),
        default=[{"name": script_name} for script_name in settings.SCRIPT_HOOKS.split(",")]
        if settings.SCRIPT_HOOKS
        else [],
    )

    # 以下非参数传值
    op_type = serializers.CharField(label=_("操作类型"), required=False)
    node_type = serializers.CharField(label=_("节点类型"), required=False)

    def validate(self, attrs):
        # 取得节点类型
        job_type_slices = attrs["job_type"].split("_")
        attrs["op_type"] = job_type_slices[0]
        attrs["node_type"] = job_type_slices[-1]

        # 替换PROXY必须填写replace_host_id
        if attrs["job_type"] == constants.JobType.REPLACE_PROXY and not attrs.get("replace_host_id"):
            raise ValidationError(_("替换PROXY必须填写replace_host_id"))

        if attrs["op_type"] in self.op_not_need_identity:
            # 回填bk_host_id
            self.backfill_bk_host_id(attrs["hosts"])
            # 回填使用映射的主机的ap id
            self.backfill_ap_id(attrs["hosts"])

        bk_biz_ids = set()
        expected_bk_host_ids_gby_bk_biz_id: typing.Dict[int, typing.List[int]] = defaultdict(list)
        cipher = tools.HostTools.get_asymmetric_cipher()
        fields_need_decrypt = ["password", "key"]
        # 密码解密
        for host in attrs["hosts"]:
            bk_biz_ids.add(host.get("bk_biz_id"))
            # 解密
            for field_need_decrypt in fields_need_decrypt:
                if not isinstance(host.get(field_need_decrypt), str):
                    continue
                host[field_need_decrypt] = tools.HostTools.decrypt_with_friendly_exc_handle(
                    cipher=cipher, encrypt_message=host[field_need_decrypt], raise_exec=ValidationError
                )

            if attrs["op_type"] not in [constants.OpType.INSTALL, constants.OpType.REPLACE]:
                if "bk_biz_id" not in host:
                    raise ValidationError(_("主机信息缺少业务ID（bk_biz_id）"))
                expected_bk_host_ids_gby_bk_biz_id[host["bk_biz_id"]].append(host["bk_host_id"])

        if attrs["op_type"] not in [constants.OpType.INSTALL, constants.OpType.REPLACE]:
            # 差量同步主机
            bulk_differential_sync_biz_hosts(expected_bk_host_ids_gby_bk_biz_id)

        set_agent_setup_info_to_attrs(attrs)

        gse_v2_ap_ids: typing.List[int] = list(
            models.AccessPoint.objects.filter(gse_version=GseVersion.V2.value).values_list("id", flat=True)
        )
        if not gse_v2_ap_ids or len(gse_v2_ap_ids) == models.AccessPoint.objects.count():
            # 没有 V2 接入点或者全部为 V2 接入点时，无需进行重定向处理
            return attrs

        try:
            gray_ap_map: typing.Dict[int, int] = GrayHandler.get_gray_ap_map()
        except Exception:
            # 没有配置接入点映射时，直接返回
            return attrs

        gray_scope_set: typing.Set[int] = set(GrayTools.get_or_create_gse2_gray_scope_list())

        # 进入灰度的管控区域，所属管控区域主机接入点重定向到 V2
        gse_v2_cloud_ids: typing.Set[int] = set(
            models.Cloud.objects.filter(ap_id__in=gse_v2_ap_ids).values_list("bk_cloud_id", flat=True)
        )

        for host in attrs["hosts"]:
            # 忽略没有选择接入点的情况
            if not host.get("ap_id"):
                continue

            # 适配标准运维仅安装Agent流程
            # AP_ID 偏移规则 ap_id * 100000 + install_channel_id
            if host["ap_id"] >= INSTALL_OTHER_AGENT_AP_ID_OFFSET:
                offset_ap_id: int = host["ap_id"]
                host["is_need_inject_ap_id"] = True
                host["ap_id"] = int(offset_ap_id / INSTALL_OTHER_AGENT_AP_ID_OFFSET)
                install_channel_id = int(offset_ap_id % INSTALL_OTHER_AGENT_AP_ID_OFFSET)
                if install_channel_id != 0:
                    host["install_channel_id"] = install_channel_id

            # 1. 进入灰度的管控区域，所属管控区域主机需要重定向接入点到 V2
            # 2. 业务已进入灰度，主机接入点重定向到 V2
            elif host["bk_cloud_id"] in gse_v2_cloud_ids or host["bk_biz_id"] in gray_scope_set:
                host["ap_id"] = gray_ap_map.get(host["ap_id"], host["ap_id"])

        return attrs


class OperateHostSerializer(serializers.Serializer):
    """
    操作类任务主机序列化器
    """

    bk_host_id = serializers.IntegerField(label=_("主机ID"), required=False)
    ap_id = serializers.IntegerField(label=_("接入点ID"), required=False)
    bk_cloud_id = serializers.IntegerField(label=_("管控区域ID"), required=False)
    inner_ip = serializers.IPAddressField(label=_("内网IP"), required=False, allow_blank=True, protocol="ipv4")
    inner_ipv6 = serializers.IPAddressField(label=_("内网IPv6"), required=False, allow_blank=True, protocol="ipv6")
    is_use_ap_map = serializers.BooleanField(label=_("是否使用映射接入点"), required=False, default=False)

    # 以下参数不需要用户传入
    is_need_inject_ap_id = serializers.BooleanField(label=_("是否需要注入ap_id到meta"), required=False, default=False)

    def validate(self, attrs):
        # 计算is_need_inject_ap_id参数
        basic.ipv6_formatter(data=attrs, ipv6_field_names=["inner_ipv6"])

        if attrs.get("ap_id") is not None or attrs["is_use_ap_map"]:
            attrs["is_need_inject_ap_id"] = True
        if all(
            [
                attrs.get("bk_host_id") is None,
                all(
                    [
                        attrs.get("bk_cloud_id") is None,
                        attrs.get("inner_ip") is None or attrs.get("inner_ipv6") is None,
                    ]
                ),
            ]
        ):
            raise ValidationError(_("bk_host_id 或者 管控区域加IP组合必须选择一种"))

        return attrs


class OperateSerializer(InstallBaseSerializer):
    agent_setup_info = AgentSetupInfoSerializer(label=_("Agent 设置信息"), required=False)
    job_type = serializers.ChoiceField(label=_("任务类型"), choices=list(constants.JOB_TYPE_DICT))
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    version = serializers.ListField(label=_("Agent版本"), required=False)
    conditions = serializers.ListField(label=_("搜索条件"), required=False, child=serializers.DictField())
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False, child=serializers.IntegerField())
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False, child=serializers.IntegerField())
    hosts = OperateHostSerializer(label=_("主机信息"), required=False, many=True)
    is_install_latest_plugins = serializers.BooleanField(label=_("是否安装最新版本插件"), required=False, default=True)
    is_install_other_agent = serializers.BooleanField(label=_("是否为安装额外Agent"), required=False, default=False)

    # 以下非参数传值，通过validate方法计算转化得到
    op_type = serializers.CharField(label=_("操作类型,"), required=False)
    node_type = serializers.CharField(label=_("节点类型"), required=False)
    bk_host_ids = serializers.ListField(label=_("主机ID列表"), required=False)
    bk_biz_scope = serializers.ListField(label=_("业务ID列表"), required=False)

    def validate(self, attrs):
        # 取得操作类型
        attrs["op_type"] = attrs["job_type"].split("_")[0]
        attrs["node_type"] = attrs["job_type"].split("_")[1]

        if attrs["op_type"] == "INSTALL":
            raise ValidationError(_("该接口不可用于安装"))
        if attrs["op_type"] == "REPLACE":
            raise ValidationError(_("该接口不可用于替换代理"))

        if attrs.get("exclude_hosts") is not None and attrs.get("bk_host_id") is not None:
            raise ValidationError(_("跨页全选模式下不允许传bk_host_id参数"))
        if all(
            [
                attrs.get("exclude_hosts") is None,
                attrs.get("bk_host_id") is None,
                attrs.get("hosts") is None,
            ]
        ):
            raise ValidationError(_("必须选择一种模式(【是否跨页全选】)"))

        if attrs.get("hosts", []):
            # 回填bk_host_id
            self.backfill_bk_host_id(attrs["hosts"])
            # 回填使用映射的主机的ap id
            self.backfill_ap_id(attrs["hosts"])

        if attrs["node_type"] == constants.NodeType.PROXY:
            # 是否为针对代理的操作，用户有权限获取的业务
            # 格式 { bk_biz_id: bk_biz_name , ...}
            user_biz = CmdbHandler().biz_id_name({"action": constants.IamActionType.proxy_operate})
            filter_node_types = [constants.NodeType.PROXY]
            is_proxy = True
        else:
            # 用户有权限获取的业务
            # 格式 { bk_biz_id: bk_biz_name , ...}
            user_biz = CmdbHandler().biz_id_name({"action": constants.IamActionType.agent_operate})
            filter_node_types = [constants.NodeType.AGENT, constants.NodeType.PAGENT]
            is_proxy = False

        host_info: typing.Dict[int, typing.Dict[str, typing.Any]] = {
            _host["bk_host_id"]: _host for _host in attrs.get("hosts", [])
        }

        if attrs.get("exclude_hosts") is not None:
            # 跨页全选
            db_host_sql = (
                HostQuerySqlHelper.multiple_cond_sql(params=attrs, biz_scope=user_biz.keys(), is_proxy=is_proxy)
                .exclude(bk_host_id__in=attrs.get("exclude_hosts", []))
                .values("bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "node_type", "os_type")
            )

        else:
            # 不是跨页全选
            input_bk_host_ids: typing.List[int] = attrs.get("bk_host_id", []) or host_info.keys()
            db_host_sql = models.Host.objects.filter(
                bk_host_id__in=input_bk_host_ids, node_type__in=filter_node_types
            ).values("bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "node_type", "os_type")

        db_hosts, bk_biz_scope = validator.operate_validator(list(db_host_sql), host_info=host_info)
        attrs["hosts"] = db_hosts
        attrs["bk_biz_scope"] = bk_biz_scope

        set_agent_setup_info_to_attrs(attrs)

        gse_v2_ap_ids: typing.List[int] = list(
            models.AccessPoint.objects.filter(gse_version=GseVersion.V2.value).values_list("id", flat=True)
        )
        if not gse_v2_ap_ids or len(gse_v2_ap_ids) == models.AccessPoint.objects.count():
            # 没有 V2 接入点或者全部为 V2 接入点时，无需进行重定向处理
            return attrs

        host_ids: typing.List[int] = [host_info["bk_host_id"] for host_info in db_hosts]

        # 进入灰度的管控区域，所属管控区域主机接入点重定向到 V2
        gse_v2_cloud_ids: typing.Set[int] = set(
            models.Cloud.objects.filter(ap_id__in=gse_v2_ap_ids).values_list("bk_cloud_id", flat=True)
        )
        gse_v2_cloud_host_ids: typing.List[int] = list(
            models.Host.objects.filter(bk_host_id__in=host_ids, bk_cloud_id__in=gse_v2_cloud_ids).values_list(
                "bk_host_id", flat=True
            )
        )
        if gse_v2_cloud_host_ids:
            # TODO: 正式启用灰度功能后此处需要去掉try
            try:
                update_result = GrayHandler.update_host_ap_by_host_ids(
                    gse_v2_cloud_host_ids, bk_biz_scope, is_biz_gray=False, rollback=False
                )
                GrayHandler.activate(host_nodes=update_result["host_nodes"], rollback=False, only_status=True)
            except ApiError:
                pass

        # 业务已进入灰度，主机接入点重定向到 V2
        gray_bk_biz_scope: typing.Set[int] = set(GrayTools.get_or_create_gse2_gray_scope_list(get_cache=True)) & set(
            bk_biz_scope
        )
        gse_v2_default_area_host_ids: typing.List[int] = list(
            models.Host.objects.filter(bk_biz_id__in=gray_bk_biz_scope, bk_host_id__in=host_ids).values_list(
                "bk_host_id", flat=True
            )
        )
        if gse_v2_default_area_host_ids:
            # TODO: 正式启用灰度功能后此处需要去掉try
            try:
                update_result = GrayHandler.update_host_ap_by_host_ids(
                    gse_v2_default_area_host_ids, gray_bk_biz_scope, is_biz_gray=False, rollback=False
                )
                GrayHandler.activate(host_nodes=update_result["host_nodes"], rollback=False, only_status=True)
            except ApiError:
                pass

        return attrs


class RetrieveSerializer(serializers.Serializer):
    conditions = serializers.ListField(label=_("搜索条件"), required=False, child=serializers.DictField())
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    start = serializers.IntegerField(label=_("开始位置参数优先page使用"), required=False, min_value=1)


class FetchCommandSerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(label=_("主机ID"), required=True)
    is_uninstall = serializers.BooleanField(required=False, default=False)


class JobInstancesOperateSerializer(serializers.Serializer):
    instance_id_list = serializers.ListField(label=_("任务实例ID列表"), required=False)


class JobInstanceOperateSerializer(serializers.Serializer):
    instance_id = serializers.CharField(label=_("任务实例ID"))
