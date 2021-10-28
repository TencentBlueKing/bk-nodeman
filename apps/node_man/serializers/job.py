# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.exceptions import ValidationError
from apps.node_man import constants, tools


class SortSerializer(serializers.Serializer):
    head = serializers.ChoiceField(label=_("排序字段"), choices=list(constants.HEAD_TUPLE))
    sort_type = serializers.ChoiceField(label=_("排序类型"), choices=list(constants.SORT_TUPLE))


class ListSerializer(serializers.Serializer):
    job_id = serializers.ListField(label=_("任务ID"), required=False)
    status = serializers.ListField(label=_("状态"), required=False)
    created_by = serializers.ListField(label=_("执行者"), required=False)
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
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


class HostSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"))
    bk_cloud_id = serializers.IntegerField(label=_("云区域ID"))
    bk_host_id = serializers.IntegerField(label=_("主机ID"), required=False)
    ap_id = serializers.IntegerField(label=_("接入点ID"), required=False)
    install_channel_id = serializers.IntegerField(label=_("安装通道ID"), required=False, allow_null=True)
    inner_ip = serializers.IPAddressField(label=_("内网IP"))
    outer_ip = serializers.IPAddressField(label=_("外网IP"), required=False)
    login_ip = serializers.IPAddressField(label=_("登录IP"), required=False)
    data_ip = serializers.IPAddressField(label=_("数据IP"), required=False)
    os_type = serializers.ChoiceField(label=_("操作系统"), choices=list(constants.OS_TUPLE))
    auth_type = serializers.ChoiceField(label=_("认证类型"), choices=list(constants.AUTH_TUPLE), required=False)
    account = serializers.CharField(label=_("账户"), required=False, allow_blank=True)
    password = serializers.CharField(label=_("密码"), required=False, allow_blank=True)
    port = serializers.IntegerField(label=_("端口"), required=False)
    key = serializers.CharField(label=_("密钥"), required=False, allow_blank=True)
    is_manual = serializers.BooleanField(label=_("是否手动模式"), required=False, default=False)
    retention = serializers.IntegerField(label=_("密码保留天数"), required=False)
    peer_exchange_switch_for_agent = serializers.IntegerField(label=_("加速设置"), required=False, default=1)
    bt_speed_limit = serializers.IntegerField(label=_("传输限速"), required=False)
    data_path = serializers.CharField(label=_("数据文件路径"), required=False, allow_blank=True)

    def validate(self, attrs):
        # 获取任务类型，如果是除安装以外的操作，则密码和秘钥可以为空
        job_type = self.root.initial_data.get("job_type", "")
        op_type = job_type.split("_")[0]

        op_not_need_identity = [
            constants.OpType.REINSTALL,
            constants.OpType.RESTART,
            constants.OpType.UPGRADE,
            constants.OpType.UNINSTALL,
            constants.OpType.RELOAD,
        ]

        if op_type in op_not_need_identity and not attrs.get("bk_host_id"):
            raise ValidationError(_("{op_type} 操作必须填写bk_host_id.").format(op_type=op_type))
        if (
            not attrs.get("is_manual")
            and not attrs.get("auth_type")
            and job_type not in [constants.JobType.RELOAD_AGENT, constants.JobType.RELOAD_PROXY]
        ):
            raise ValidationError(_("{op_type} 操作必须填写认证类型.").format(op_type=op_type))

        # identity校验
        if op_type not in op_not_need_identity and not attrs.get("is_manual"):
            if not attrs.get("password") and attrs["auth_type"] == constants.AuthType.PASSWORD:
                raise ValidationError(_("密码认证方式必须填写密码"))
            if not attrs.get("key") and attrs["auth_type"] == constants.AuthType.KEY:
                raise ValidationError(_("密钥认证方式必须上传密钥"))
            if attrs.get("account") is None or attrs.get("port") is None:
                raise ValidationError(_("必须上传账号和端口"))

        # 直连区域必须填写Ap_id
        if attrs["bk_cloud_id"] == int(constants.DEFAULT_CLOUD) and attrs.get("ap_id") is None:
            raise ValidationError(_("直连区域必须填写Ap_id."))

        # 去除空值
        if attrs.get("key") == "":
            attrs.pop("key")
        if attrs.get("password") == "":
            attrs.pop("password")

        return attrs


class InstallSerializer(serializers.Serializer):
    job_type = serializers.ChoiceField(label=_("任务类型"), choices=list(constants.JOB_TYPE_DICT))
    hosts = HostSerializer(label=_("主机信息"), many=True)
    replace_host_id = serializers.IntegerField(label=_("被替换的Proxy主机ID"), required=False)

    # 以下非参数传值
    op_type = serializers.CharField(label=_("操作类型"), required=False)
    node_type = serializers.CharField(label=_("节点类型"), required=False)
    tcoa_ticket = serializers.CharField(label=_("OA Ticket"), required=False)

    def validate(self, attrs):
        # 取得节点类型
        job_type_slices = attrs["job_type"].split("_")
        attrs["op_type"] = job_type_slices[0]
        attrs["node_type"] = job_type_slices[-1]

        # 替换PROXY必须填写replace_host_id
        if attrs["job_type"] == constants.JobType.REPLACE_PROXY and not attrs.get("replace_host_id"):
            raise ValidationError(_("替换PROXY必须填写replace_host_id."))

        rsa_util = tools.HostTools.get_rsa_util()
        fields_need_decrypt = ["password", "key"]
        # 密码解密
        for host in attrs["hosts"]:
            for field_need_decrypt in fields_need_decrypt:
                if not isinstance(host.get(field_need_decrypt), str):
                    continue
                host[field_need_decrypt] = tools.HostTools.decrypt_with_friendly_exc_handle(
                    rsa_util=rsa_util, encrypt_message=host[field_need_decrypt], raise_exec=ValidationError
                )
        return attrs


class OperateSerializer(serializers.Serializer):
    job_type = serializers.ChoiceField(label=_("任务类型"), choices=list(constants.JOB_TYPE_DICT))
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    version = serializers.ListField(label=_("Agent版本"), required=False)
    conditions = serializers.ListField(label=_("搜索条件"), required=False)
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False)
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False)

    # 以下非参数传值
    op_type = serializers.CharField(label=_("操作类型,"), required=False)
    node_type = serializers.CharField(label=_("节点类型"), required=False)

    def validate(self, attrs):
        # 取得操作类型
        attrs["op_type"] = attrs["job_type"].split("_")[0]
        attrs["node_type"] = attrs["job_type"].split("_")[1]

        if attrs["op_type"] == "INSTALL":
            raise ValidationError(_("该接口不可用于安装."))
        if attrs["op_type"] == "REPLACE":
            raise ValidationError(_("该接口不可用于替换代理."))

        if attrs.get("exclude_hosts") is not None and attrs.get("bk_host_id") is not None:
            raise ValidationError(_("跨页全选模式下不允许传bk_host_id参数."))
        if attrs.get("exclude_hosts") is None and attrs.get("bk_host_id") is None:
            raise ValidationError(_("必须选择一种模式(【是否跨页全选】)"))
        return attrs


class RetrieveSerializer(serializers.Serializer):
    conditions = serializers.ListField(label=_("搜索条件"), required=False)
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)


class FetchCommandSerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(label=_("主机ID"), required=True)
    is_uninstall = serializers.BooleanField(required=False, default=False)
