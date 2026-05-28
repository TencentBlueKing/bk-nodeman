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
from typing import List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.backend.subscription.steps.agent_adapter.base import AgentSetupTools
from apps.exceptions import ValidationError
from apps.node_man.constants import (
    GSE_PORT_DEFAULT_VALUE,
    GSE_V2_PORT_DEFAULT_VALUE,
    IamActionType,
    OsType,
)
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import AccessPoint, GlobalSettings
from apps.utils import basic
from apps.utils.local import get_request_username
from apps.utils.security import is_safe_url
from env.constants import GseVersion


def validate_agent_config(agent_config):
    """
    校验 agent_config 字段的合法性和安全性
    
    Args:
        agent_config: Agent配置字典，格式为 {os_type: {config_key: config_value}}
    
    Returns:
        校验后的 agent_config
    
    Raises:
        ValidationError: 当配置不合法时抛出异常
    """
    # 定义允许的操作系统类型
    allowed_os_types = {"linux", "windows", "aix", "solaris", "darwin"}
    
    # 定义每个操作系统下允许的字段及其类型
    # 完整列表，与前端表单和数据库迁移脚本保持一致
    allowed_fields = {
        "setup_path": str,          # Agent 安装路径
        "temp_path": str,            # 临时文件目录
        "log_path": str,             # 日志路径
        "data_path": str,            # 数据路径
        "run_path": str,             # 运行路径
        "hostid_path": str,          # host_id 文件路径
        "pluginipc": (str, int),     # 插件 IPC 配置（可以是路径或端口号）
        "dataipc": (str, int),       # 数据 IPC 配置（可以是路径或端口号）
        "alarm_event_data_id": int,  # 告警事件数据 ID
    }
    
    # 危险路径关键字，禁止出现在路径中
    dangerous_patterns = [
        "..",           # 路径遍历
        "~",            # 家目录
        "$(",           # 命令替换
        "`",            # 命令替换
        "|",            # 管道
        ";",            # 命令分隔符
        "&",            # 后台执行（必须放在 && 之前）
        "&&",           # 命令连接
        "||",           # 命令连接
        ">",            # 重定向
        "<",            # 重定向
        "\n",           # 换行符
        "\r",           # 回车符
        "$",            # 变量引用
        "(",            # 子shell
        ")",            # 子shell
        "{",            # 代码块
        "}",            # 代码块
        "[",            # 通配符
        "]",            # 通配符
        "!",            # 历史扩展
        # 注意：Windows 路径允许使用反斜杠（\），所以不在危险字符列表中
    ]
    
    if not isinstance(agent_config, dict):
        raise ValidationError(_("agent_config 必须是字典类型"))
    
    for os_type, config in agent_config.items():
        # 校验操作系统类型
        if os_type.lower() not in allowed_os_types:
            raise ValidationError(_("不支持的操作系统类型: {os_type}").format(os_type=os_type))
        
        if not isinstance(config, dict):
            raise ValidationError(_("操作系统 {os_type} 的配置必须是字典类型").format(os_type=os_type))
        
        for key, value in config.items():
            # 校验字段名是否合法
            if key not in allowed_fields:
                raise ValidationError(
                    _("操作系统 {os_type} 包含不支持的配置项: {key}").format(os_type=os_type, key=key)
                )
            
            # 校验字段类型
            expected_type = allowed_fields[key]
            if not isinstance(value, expected_type):
                raise ValidationError(
                    _("操作系统 {os_type} 的配置项 {key} 类型错误，期望 {expected_type}，实际为 {actual_type}").format(
                        os_type=os_type,
                        key=key,
                        expected_type=expected_type.__name__,
                        actual_type=type(value).__name__,
                    )
                )
            
            # 如果是路径类型的字段，进行安全校验
            # 注意：dataipc 和 pluginipc 既可以是路径（字符串），也可以是端口号（整数）
            # 只有值是字符串时才进行路径校验
            if key in ["setup_path", "temp_path", "log_path", "data_path", "run_path", "hostid_path"]:
                if isinstance(value, str):
                    # 检查危险字符
                    for pattern in dangerous_patterns:
                        if pattern in value:
                            raise ValidationError(
                                _("操作系统 {os_type} 的配置项 {key} 包含不安全的字符: {pattern}").format(
                                    os_type=os_type, key=key, pattern=pattern
                                )
                            )
                    
                    # Windows 路径特殊校验
                    if os_type.lower() == "windows":
                        # 允许反斜杠，但要防止路径遍历
                        # 将路径标准化，检查是否包含路径遍历
                        normalized_path = value.replace("\\", "/")
                        if ".." in normalized_path or "~" in normalized_path:
                            raise ValidationError(
                                _("操作系统 {os_type} 的配置项 {key} 包含不安全的路径遍历字符").format(
                                    os_type=os_type, key=key
                                )
                            )
                    
                    # 检查是否以 / 或盘符开头（绝对路径）
                    if os_type.lower() == "windows":
                        # Windows 路径应该以盘符开头，如 C:\ 或 C:/
                        if not (value[0].isalpha() and value[1:3] in [":\\", ":/"]):
                            # 相对路径也不允许
                            if not (value.startswith(".\\") or value.startswith("./")):
                                raise ValidationError(
                                    _("操作系统 {os_type} 的配置项 {key} 必须是绝对路径").format(
                                        os_type=os_type, key=key
                                    )
                                )
                    else:
                        # Linux/Unix 路径应该以 / 开头
                        if not value.startswith("/"):
                            raise ValidationError(
                                _("操作系统 {os_type} 的配置项 {key} 必须是绝对路径").format(
                                    os_type=os_type, key=key
                                )
                            )
            
            # dataipc 和 pluginipc 的特殊处理：
            # - 如果是整数则跳过路径校验
            # - 如果是字符串且可以解析为纯数字（端口号），也跳过路径校验
            # - 如果是字符串且不是纯数字，则进行路径校验
            elif key in ["dataipc", "pluginipc"]:
                if isinstance(value, str):
                    # 检查是否是纯数字字符串（端口号）
                    if value.isdigit():
                        # 是纯数字字符串，作为端口号处理，跳过路径校验
                        continue
                    
                    # 不是纯数字，作为路径处理，进行路径安全校验
                    # 检查危险字符
                    for pattern in dangerous_patterns:
                        if pattern in value:
                            raise ValidationError(
                                _("操作系统 {os_type} 的配置项 {key} 包含不安全的字符: {pattern}").format(
                                    os_type=os_type, key=key, pattern=pattern
                                )
                            )
                    
                    # Windows 路径特殊校验
                    if os_type.lower() == "windows":
                        # 允许反斜杠，但要防止路径遍历
                        normalized_path = value.replace("\\", "/")
                        if ".." in normalized_path or "~" in normalized_path:
                            raise ValidationError(
                                _("操作系统 {os_type} 的配置项 {key} 包含不安全的路径遍历字符").format(
                                    os_type=os_type, key=key
                                )
                            )
                    
                    # 检查是否以 / 或盘符开头（绝对路径）
                    if os_type.lower() == "windows":
                        # Windows 路径应该以盘符开头，如 C:\ 或 C:/
                        if not (value[0].isalpha() and value[1:3] in [":\\", ":/"]):
                            # 相对路径也不允许
                            if not (value.startswith(".\\") or value.startswith("./")):
                                raise ValidationError(
                                    _("操作系统 {os_type} 的配置项 {key} 必须是绝对路径").format(
                                        os_type=os_type, key=key
                                    )
                                )
                    else:
                        # Linux/Unix 路径应该以 / 开头
                        if not value.startswith("/"):
                            raise ValidationError(
                                _("操作系统 {os_type} 的配置项 {key} 必须是绝对路径").format(
                                    os_type=os_type, key=key
                                )
                            )
    
    return agent_config


def validate_port_config(port_config):
    """
    校验 port_config 字段的合法性和安全性
    
    Args:
        port_config: 端口配置字典
    
    Returns:
        校验后的 port_config
    
    Raises:
        ValidationError: 当配置不合法时抛出异常
    """
    # 定义允许的端口配置字段
    allowed_fields = {
        "io_port",              # IO 端口
        "trunk_port",           # Trunk 端口
        "db_proxy_port",        # DB 代理端口
        "file_svr_port",        # 文件服务器端口
        "file_svr_port_v1",     # 文件服务器端口 V1
        "data_port",            # 数据端口
        "bt_port",              # BT 端口
        "bt_port_start",        # BT 端口起始范围
        "bt_port_end",          # BT 端口结束范围
        "agent_thrift_port",    # Agent Thrift 端口
        "btsvr_thrift_port",    # BT 服务器 Thrift 端口
        "api_server_port",      # API 服务器端口
        "proc_port",            # Proc 端口
        "tracker_port",         # Tracker 端口
        "data_prometheus_port", # 数据 Prometheus 端口
        "file_topology_bind_port",  # 文件拓扑绑定端口
        "file_metric_bind_port",    # 文件指标绑定端口
    }
    
    # 危险字符黑名单
    dangerous_patterns = [
        "$((", "$(`", "$([", "$(<", "$(>",  # 命令替换变种
        "$(", "`", "|", ";", "&", "&&", "||", ">", "<",  # 原黑名单
        "\n", "\r", "$", "(", ")", "{", "}", "[", "]", "!", "\\",
    ]
    
    if not isinstance(port_config, dict):
        raise ValidationError(_("port_config 必须是字典类型"))
    
    for key, value in port_config.items():
        # 校验字段名是否合法
        if key not in allowed_fields:
            raise ValidationError(
                _("不支持的端口配置项: {key}").format(key=key)
            )
        
        # 校验端口号必须是正整数
        if not isinstance(value, int):
            raise ValidationError(
                _("端口配置项 {key} 必须是正整数").format(key=key)
            )
        
        # 校验端口号范围（1-65535）
        if not (1 <= value <= 65535):
            raise ValidationError(
                _("端口配置项 {key} 必须在 1-65535 范围内").format(key=key)
            )
        
        # 如果值是字符串（不应该出现，但以防万一），检查危险字符
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if pattern in value:
                    raise ValidationError(
                        _("端口配置项 {key} 包含不安全的字符: {pattern}").format(
                            key=key, pattern=pattern
                        )
                    )
    
    return port_config


def validate_bscp_config(bscp_config):
    """
    校验 bscp_config 字段的合法性和安全性
    
    Args:
        bscp_config: BSCP 配置字典
    
    Returns:
        校验后的 bscp_config
    
    Raises:
        ValidationError: 当配置不合法时抛出异常
    """
    # 定义允许的 BSCP 配置字段
    allowed_fields = {
        "server_url": str,      # BSCP 服务器地址
        "config_path": str,     # 配置文件路径
        "log_path": str,        # 日志路径
        "data_path": str,       # 数据路径
    }
    
    # 危险字符黑名单（复用 agent_config 的黑名单）
    dangerous_patterns = [
        "..", "~", "$(", "`", "|", ";", "&", "&&", "||",
        ">", "<", "\n", "\r", "$", "(", ")", "{", "}",
        "[", "]", "!", "\\",
    ]
    
    if not isinstance(bscp_config, dict):
        raise ValidationError(_("bscp_config 必须是字典类型"))
    
    for key, value in bscp_config.items():
        # 校验字段名是否合法
        if key not in allowed_fields:
            raise ValidationError(
                _("不支持的 BSCP 配置项: {key}").format(key=key)
            )
        
        # 校验字段类型
        expected_type = allowed_fields[key]
        if not isinstance(value, expected_type):
            raise ValidationError(
                _("BSCP 配置项 {key} 类型错误，期望 {expected_type}，实际为 {actual_type}").format(
                    key=key,
                    expected_type=expected_type.__name__,
                    actual_type=type(value).__name__,
                )
            )
        
        # 如果是路径类型的字段，进行安全校验
        if key in ["config_path", "log_path", "data_path"]:
            if isinstance(value, str):
                # 检查危险字符
                for pattern in dangerous_patterns:
                    if pattern in value:
                        raise ValidationError(
                            _("BSCP 配置项 {key} 包含不安全的字符: {pattern}").format(
                                key=key, pattern=pattern
                            )
                        )
                
                # 检查绝对路径
                if not value.startswith("/"):
                    raise ValidationError(
                        _("BSCP 配置项 {key} 必须是绝对路径").format(key=key)
                    )
    
    return bscp_config


class ListSerializer(serializers.ModelSerializer):
    """
    AP返回数据
    """

    id = serializers.IntegerField(label=_("接入点ID"))
    name = serializers.CharField(label=_("接入点名称"))
    ap_type = serializers.CharField(label=_("接入点类型"))
    region_id = serializers.CharField(label=_("区域id"))
    city_id = serializers.CharField(label=_("城市id"))
    btfileserver = serializers.JSONField(label=_("GSE BT文件服务器列表"))
    dataserver = serializers.JSONField(label=_("GSE 数据服务器列表"))
    taskserver = serializers.JSONField(label=_("GSE 任务服务器列表"))
    zk_hosts = serializers.JSONField(label=_("ZK服务器列表"))
    zk_account = serializers.CharField(label=_("ZK账号"))
    package_inner_url = serializers.CharField(label=_("安装包内网地址"))
    package_outer_url = serializers.CharField(label=_("安装包外网地址"))
    agent_config = serializers.JSONField(label=_("Agent配置信息"))
    status = serializers.CharField(label=_("接入点状态"))
    description = serializers.CharField(label=_("接入点描述"), allow_blank=True)
    is_enabled = serializers.BooleanField(label=_("是否启用"))
    is_default = serializers.BooleanField(label=_("是否默认接入点，不可删除"))
    proxy_package = serializers.JSONField(label=_("Proxy上的安装包"))
    file_cache_dirs = serializers.SerializerMethodField(label=_("文件缓存目录"))

    def to_representation(self, instance):
        ret = super(ListSerializer, self).to_representation(instance)
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [IamActionType.ap_edit, IamActionType.ap_delete, IamActionType.ap_create, IamActionType.ap_view],
        )
        ret["permissions"] = {
            "edit": ret["id"] in perms[IamActionType.ap_edit],
            "delete": ret["id"] in perms[IamActionType.ap_delete],
            "view": ret["id"] in perms[IamActionType.ap_view],
        }
        return ret

    def get_file_cache_dirs(self, instance):
        is_legacy: bool = instance.gse_version == GseVersion.V1.value
        data_path: str = AgentSetupTools.generate_default_file_cache_dir(
            path=instance.agent_config[OsType.LINUX.lower()]["setup_path"], is_legacy=is_legacy
        )
        return data_path

    class Meta:
        model = AccessPoint
        exclude = ("zk_password",)


class UpdateOrCreateSerializer(serializers.ModelSerializer):
    """
    创建AP
    """

    class ServersSerializer(serializers.Serializer):
        inner_ip = serializers.CharField(label=_("内网IP"), required=False)
        inner_ipv6 = serializers.CharField(label=_("内网IPv6"), required=False)
        outer_ip = serializers.CharField(label=_("外网IP"), required=False)
        outer_ipv6 = serializers.CharField(label=_("外网IPv6"), required=False)
        bk_host_id = serializers.IntegerField(label=_("主机ID"), required=False)

        def validate(self, attrs):
            basic.ipv6_formatter(data=attrs, ipv6_field_names=["inner_ipv6", "outer_ipv6"])

            if not (attrs.get("inner_ip") or attrs.get("inner_ipv6")):
                raise ValidationError(_("请求参数 inner_ip 和 inner_ipv6 不能同时为空"))
            if not (attrs.get("outer_ip") or attrs.get("outer_ipv6")):
                raise ValidationError(_("请求参数 outer_ip 和 outer_ipv6 不能同时为空"))
            return attrs

    class ZKSerializer(serializers.Serializer):
        zk_ip = serializers.CharField(label=_("ZK IP地址"))
        zk_port = serializers.CharField(label=_("ZK 端口"))

    btfileserver = serializers.ListField(child=ServersSerializer())
    dataserver = serializers.ListField(child=ServersSerializer())
    taskserver = serializers.ListField(child=ServersSerializer())
    zk_hosts = serializers.ListField(child=ZKSerializer())
    zk_account = serializers.CharField(label=_("ZK账号"), required=False, allow_blank=True)
    zk_password = serializers.CharField(label=_("ZK密码"), required=False, allow_blank=True)
    agent_config = serializers.DictField(label=_("Agent配置"))
    description = serializers.CharField(label=_("接入点描述"), allow_blank=True)
    creator = serializers.JSONField(_("接入点创建者"), required=False)
    port_config = serializers.DictField(default=GSE_PORT_DEFAULT_VALUE)
    proxy_package = serializers.ListField()
    bscp_config = serializers.DictField(_("BSCP配置"), required=False)
    outer_callback_url = serializers.CharField(label=_("节点管理外网回调地址"), required=False, allow_blank=True)
    callback_url = serializers.CharField(label=_("节点管理内网回调地址"), required=False, allow_blank=True)

    def validate(self, data):
        # 校验 agent_config 的安全性
        if "agent_config" in data:
            data["agent_config"] = validate_agent_config(data["agent_config"])
        
        # 校验 port_config 的安全性
        if "port_config" in data:
            data["port_config"] = validate_port_config(data["port_config"])
        
        # 校验 bscp_config 的安全性
        if "bscp_config" in data and data["bscp_config"]:
            data["bscp_config"] = validate_bscp_config(data["bscp_config"])
        
        gse_version_list: List[str] = list(set(AccessPoint.objects.values_list("gse_version", flat=True)))
        # 存量接入点版本全部为V2新建/更新版本也为V2版本
        if GseVersion.V1.value not in gse_version_list:
            data["gse_version"] = GseVersion.V2.value
            data["port_config"] = GSE_V2_PORT_DEFAULT_VALUE

        blocked_ports: list = GlobalSettings.get_config(key=GlobalSettings.KeyEnum.AP_BLOCKED_PORTS.value, default=[])
        blocked_networks: list = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.AP_BLOCKED_NETWORKS.value, default=[]
        )
        is_ok, message = is_safe_url(
            [
                data["package_inner_url"],
                data["package_outer_url"],
                data.get("outer_callback_url", ""),
                data.get("callback_url", ""),
            ],
            blocked_ports=blocked_ports,
            blocked_networks=blocked_networks,
        )
        if not is_ok:
            raise ValidationError(message)

        return data

    class Meta:
        fields = "__all__"
        model = AccessPoint
