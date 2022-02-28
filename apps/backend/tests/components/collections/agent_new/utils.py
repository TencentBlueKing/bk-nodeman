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

import base64
import copy
import os
import random
import textwrap
from abc import ABC
from typing import Any, Dict, List, Optional, Type

import mock
from django.conf import settings
from django.db.models import Model
from django.utils import timezone
from django.utils.translation import get_language

from apps.backend.components.collections import agent_new
from apps.backend.subscription import tools
from apps.core.concurrent.controller import ConcurrentController
from apps.mock_data import common_unit, utils
from apps.node_man import constants, models
from apps.utils import basic, concurrent
from apps.utils.unittest.testcase import CustomAPITestCase

# 目标主机信息
from pipeline.component_framework.test import ComponentTestMixin

AGENT_INSTANCE_HOST_INFO = {
    "is_manual": False,
    "ap_id": common_unit.host.HOST_MODEL_DATA["ap_id"],
    "username": utils.DEFAULT_USERNAME,
    "account": constants.ACCOUNT_MAP[common_unit.host.HOST_MODEL_DATA["os_type"]],
    "os_type": common_unit.host.HOST_MODEL_DATA["os_type"],
    "bk_os_type": constants.BK_OS_TYPE[common_unit.host.HOST_MODEL_DATA["os_type"]],
    "host_node_type": constants.NodeType.AGENT,
    "login_ip": utils.DEFAULT_IP,
    "bk_host_innerip": utils.DEFAULT_IP,
    "bk_host_outerip": utils.DEFAULT_IP,
    "port": 22,
    "password": base64.b64encode("password".encode()).decode(),
    "key": base64.b64encode("password:::key".encode()).decode(),
    "auth_type": constants.AuthType.PASSWORD,
    "retention": 1,
    "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
    "bk_biz_name": utils.DEFAULT_BK_BIZ_NAME,
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "bk_cloud_name": constants.DEFAULT_CLOUD_NAME,
    "bk_supplier_account": constants.DEFAULT_SUPPLIER_ID,
    "peer_exchange_switch_for_agent": True,
}


class SshManMockClient(utils.BaseMockClient):
    def __init__(
        self,
        get_and_set_prompt_return: Optional[utils.MockReturn] = None,
        send_cmd_return_return: Optional[utils.MockReturn] = None,
        safe_close_return: Optional[utils.MockReturn] = None,
        ssh_return: Optional[utils.MockReturn] = None,
    ):
        super().__init__()
        self.get_and_set_prompt = self.generate_magic_mock(mock_return_obj=get_and_set_prompt_return)
        self.send_cmd = self.generate_magic_mock(mock_return_obj=send_cmd_return_return)
        self.safe_close = self.generate_magic_mock(mock_return_obj=safe_close_return)
        self.ssh = self.generate_magic_mock(mock_return_obj=ssh_return)


class AgentTestObjFactory:

    # 主机实例信息，如需创建数据，请通过深拷贝的方式复制
    BASE_INSTANCE_HOST_INFO: Dict[str, Any] = copy.deepcopy(AGENT_INSTANCE_HOST_INFO)
    # 随机生成的起始主机ID
    RANDOM_BEGIN_HOST_ID: int = random.randint(int(1e2), int(1e5))

    # 构造的主机数
    init_host_num: Optional[int] = None
    # 操作系统可选项
    host_os_type_options: Optional[List[int]] = None

    sub_obj: Optional[models.Subscription] = None
    sub_task_obj: Optional[models.SubscriptionTask] = None
    sub_step_objs: List[models.SubscriptionStep] = []
    sub_inst_record_objs: List[models.SubscriptionInstanceRecord] = []
    sub_inst_record_ids: List[int] = []

    bk_host_ids: List[int] = []
    host_objs: List[models.Host] = []
    identity_data_objs: List[models.IdentityData] = []

    def __init__(self):
        self.init_host_num = 1
        self.host_os_type_options = [constants.OsType.LINUX]

    @classmethod
    def bulk_create_model(cls, model: Type[Model], create_data_list: List[Dict]):
        objs_to_be_created = []
        for create_data in create_data_list:
            objs_to_be_created.append(model(**create_data))
        model.objects.bulk_create(objs_to_be_created)

    @classmethod
    def fill_mock_ip(cls, host_related_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ip_field_names = ["inner_ip", "outer_ip", "login_ip", "data_ip", "bk_host_innerip", "bk_host_outerip"]
        default_ip_tmpl = "127.0.0.{index}"
        for index, host_data in enumerate(host_related_data_list, 1):
            ip = default_ip_tmpl.format(index=index)
            for ip_field_name in ip_field_names:
                if ip_field_name not in host_data:
                    continue
                host_data[ip_field_name] = ip
        return host_related_data_list

    @classmethod
    def fill_mock_bk_host_id(cls, host_related_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for index, host_data in enumerate(host_related_data_list):
            host_data.update(bk_host_id=cls.RANDOM_BEGIN_HOST_ID + index)
        return host_related_data_list

    def fill_host_os_type(self, instance_host_info_list) -> List[Dict[str, Any]]:
        for instance_host_info in instance_host_info_list:
            os_type = random.choice(self.host_os_type_options)
            instance_host_info.update(os_type=os_type, bk_os_type=constants.BK_OS_TYPE.get(os_type))
        return instance_host_info_list

    @classmethod
    def structure_action(cls) -> Dict[str, str]:
        return {constants.SubStepType.AGENT.lower(): constants.JobType.INSTALL_AGENT}

    @classmethod
    def get_instance_id_by_node(cls, object_type: str, node_type: str, node: Dict[str, Any]) -> str:
        create_node_base_data = {"object_type": object_type, "node_type": node_type}
        # 单元测试仅考虑两种情况，初次安装Agent（注册CMDB无bk_host_id）及有 bk_host_id 的情况
        # 其他场景应该在订阅创建等流程进行测试
        if "bk_host_id" in node:
            create_node_base_data["bk_host_id"] = node["bk_host_id"]
        else:
            create_node_base_data.update({"bk_cloud_id": node["bk_cloud_id"], "ip": node["ip"]})
        return tools.create_node_id(create_node_base_data)

    def structure_host_data_list(self) -> List[Dict[str, Any]]:
        host_data_list = []
        instance_host_info_list = self.structure_instance_host_info_list()
        for instance_host_info in instance_host_info_list:
            extra_data = {
                "peer_exchange_switch_for_agent": instance_host_info.get("peer_exchange_switch_for_agent", True),
                "bt_speed_limit": instance_host_info.get("bt_speed_limit", 0),
            }
            if instance_host_info.get("data_path"):
                extra_data.update({"data_path": instance_host_info.get("data_path")})

            host_data_list.append(
                {
                    "bk_biz_id": instance_host_info["bk_biz_id"],
                    "bk_cloud_id": instance_host_info["bk_cloud_id"],
                    "bk_host_id": instance_host_info["bk_host_id"],
                    "inner_ip": instance_host_info.get("bk_host_innerip", ""),
                    "outer_ip": instance_host_info.get("bk_host_outerip", ""),
                    "login_ip": instance_host_info.get("login_ip", ""),
                    "data_ip": instance_host_info.get("data_ip", ""),
                    "is_manual": instance_host_info.get("is_manual", False),
                    "os_type": instance_host_info["os_type"],
                    "node_type": instance_host_info["host_node_type"],
                    "ap_id": instance_host_info["ap_id"],
                    "install_channel_id": instance_host_info.get("install_channel_id"),
                    "upstream_nodes": instance_host_info.get("upstream_nodes", []),
                    "updated_at": timezone.now(),
                    "extra_data": extra_data,
                }
            )

        return host_data_list

    def structure_identity_data_list(self, host_objs: List[models.Host]) -> List[Dict[str, Any]]:
        """
        构造主机认证信息列表
        :param host_objs: 主机对象列表
        :return: 主机认证信息列表
        """
        identity_data_list = []
        host_key__host_data_map: Dict[str, Dict[str, Any]] = {
            f"{host_info['bk_cloud_id']}-{host_info['bk_host_innerip']}": host_info
            for host_info in self.structure_instance_host_info_list()
        }
        for host_obj in host_objs:
            host_key = f"{host_obj.bk_cloud_id}-{host_obj.inner_ip}"
            host_info = host_key__host_data_map[host_key]
            identity_data = {
                "bk_host_id": host_obj.bk_host_id,
                "auth_type": host_info["auth_type"],
                "account": host_info["account"],
                "password": base64.b64decode(host_info.get("password", "")).decode(),
                "port": host_info.get("port"),
                "key": base64.b64decode(host_info.get("key", "")).decode(),
                "retention": host_info.get("retention", 1),
                "extra_data": host_info.get("extra_data", {}),
                "updated_at": timezone.now(),
            }
            identity_data_list.append(identity_data)

        return identity_data_list

    def structure_instance_host_info_list(self) -> List[Dict[str, Any]]:
        """
        构造Agent安装目标实例，如需修改测试样例，可以继承该类，覆盖该方法
        :return:
        """
        instance_host_info_list = []
        for __ in range(0, self.init_host_num):
            instance_host_info = copy.deepcopy(self.BASE_INSTANCE_HOST_INFO)
            instance_host_info_list.append(instance_host_info)
        return self.fill_mock_ip(self.fill_host_os_type(self.fill_mock_bk_host_id(instance_host_info_list)))

    def structure_sub_data(self) -> Dict[str, Any]:
        base_sub_data = basic.remove_keys_from_dict(
            origin_data=common_unit.subscription.SUBSCRIPTION_MODEL_DATA, keys=["id"]
        )
        base_sub_data.update(
            {
                "node_type": models.Subscription.NodeType.INSTANCE,
                "object_type": models.Subscription.ObjectType.HOST,
                "nodes": [
                    {
                        "bk_supplier_account": constants.DEFAULT_SUPPLIER_ID,
                        "bk_cloud_id": instance_host_info["bk_cloud_id"],
                        "ip": instance_host_info["bk_host_innerip"],
                        "instance_info": instance_host_info,
                    }
                    for instance_host_info in self.structure_instance_host_info_list()
                ],
            }
        )
        return base_sub_data

    def structure_sub_task_data(self) -> Dict[str, Any]:
        sub_task_data = basic.remove_keys_from_dict(
            origin_data=common_unit.subscription.SUB_TASK_MODEL_DATA, keys=["id"]
        )
        sub_task_data.update(
            {
                "subscription_id": self.sub_obj.id,
                "scope": {
                    "nodes": self.sub_obj.nodes,
                    "bk_biz_id": self.sub_obj.bk_biz_id,
                    "object_type": self.sub_obj.object_type,
                    "node_type": self.sub_obj.node_type,
                    "need_register": True,
                },
                "is_auto_trigger": False,
            }
        )

        actions: Dict[str, Dict[str, str]] = {}
        for node in self.sub_obj.nodes:
            instance_id = self.get_instance_id_by_node(
                object_type=self.sub_obj.object_type, node_type=self.sub_obj.node_type, node=node
            )
            actions[instance_id] = self.structure_action()

        return sub_task_data

    def structure_sub_step_data_list(self) -> List[Dict[str, Any]]:
        sub_step_data = basic.remove_keys_from_dict(
            origin_data=common_unit.subscription.SUB_AGENT_STEP_MODEL_DATA, keys=["id"]
        )
        sub_step_data.update(
            {
                "subscription_id": self.sub_obj.id,
                "config": {"job_type": constants.JobType.INSTALL_AGENT},
            }
        )
        return [sub_step_data]

    def structure_sub_inst_data_list(self):
        sub_inst_data_list = []
        steps = []
        for sub_step_obj in self.sub_step_objs:
            steps.append(
                {
                    "id": sub_step_obj.step_id,
                    "type": sub_step_obj.type,
                    # 不考虑插件下发的自动巡检（不指定job_type）
                    "action": sub_step_obj.config.get("job_type"),
                }
            )
        for node in self.sub_obj.nodes:
            instance_id = self.get_instance_id_by_node(
                object_type=self.sub_obj.object_type, node_type=self.sub_obj.node_type, node=node
            )
            sub_inst_data = basic.remove_keys_from_dict(
                origin_data=common_unit.subscription.SUB_INST_RECORD_MODEL_DATA, keys=["id"]
            )
            sub_inst_data.update(
                {
                    "task_id": self.sub_task_obj.id,
                    "subscription_id": self.sub_obj.id,
                    "is_latest": True,
                    "instance_id": instance_id,
                    "instance_info": {
                        "host": node["instance_info"],
                        "scope": [{"ip": node["ip"], "bk_cloud_id": node["bk_cloud_id"]}],
                    },
                    "steps": steps,
                }
            )
            sub_inst_data_list.append(sub_inst_data)
        return sub_inst_data_list

    def init_sub_related_data_in_db(self):
        """
        初始化订阅相关数据，数据创建具有前后依赖关系
        :return:
        """
        self.sub_obj = models.Subscription.objects.create(**self.structure_sub_data())
        self.sub_task_obj = models.SubscriptionTask.objects.create(**self.structure_sub_task_data())

        self.bulk_create_model(model=models.SubscriptionStep, create_data_list=self.structure_sub_step_data_list())
        self.sub_step_objs = models.SubscriptionStep.objects.filter(subscription_id=self.sub_obj.id)

        self.bulk_create_model(
            model=models.SubscriptionInstanceRecord, create_data_list=self.structure_sub_inst_data_list()
        )
        self.sub_inst_record_objs = models.SubscriptionInstanceRecord.objects.filter(
            subscription_id=self.sub_obj.id, task_id=self.sub_task_obj.id
        )
        self.sub_inst_record_ids = [sub_inst_obj.id for sub_inst_obj in self.sub_inst_record_objs]

    def init_host_related_data_in_db(self):
        """
        初始化主机相关数据
        :return:
        """
        host_data_list = self.structure_host_data_list()
        self.bk_host_ids = [host_data["bk_host_id"] for host_data in host_data_list]
        self.bulk_create_model(model=models.Host, create_data_list=host_data_list)
        self.host_objs = models.Host.objects.filter(bk_host_id__in=self.bk_host_ids)

        identity_data_list = self.structure_identity_data_list(host_objs=self.host_objs)
        self.bulk_create_model(model=models.IdentityData, create_data_list=identity_data_list)
        self.identity_data_objs = models.IdentityData.objects.filter(bk_host_id__in=self.bk_host_ids)

    def init_db(self):
        """
        初始化DB测试数据
        :return:
        """
        self.init_host_related_data_in_db()
        self.init_sub_related_data_in_db()
        self.check_init_db()

    def check_init_db(self):
        """
        对构造数据执行基础断言，保证初始化数据的准确性
        :return:
        """

        def _check_objs_fields_type(_objs: List[Model], _field__type__map: Dict[str, type]):
            for _obj in _objs:
                for _field, _type in _field__type__map.items():
                    _id = getattr(_obj, _field)
                    if _id is None and _type is not None:
                        raise KeyError(f"obj -> {_obj} does not have field -> {_field}")
                    _actual_type = type(_id)
                    if _actual_type != _type:
                        raise ValueError(
                            f"obj -> {_obj}, field -> {_field} except {_type} but get {_actual_type}(value -> {_id})"
                        )

        assert self.sub_step_objs
        assert self.sub_inst_record_objs
        assert self.host_objs
        assert self.bk_host_ids
        assert self.identity_data_objs

        _check_objs_fields_type(
            _objs=self.sub_inst_record_objs, _field__type__map={"id": int, "subscription_id": int, "task_id": int}
        )
        _check_objs_fields_type(
            _objs=self.sub_step_objs, _field__type__map={"id": int, "subscription_id": int, "step_id": str, "type": str}
        )
        _check_objs_fields_type(_objs=self.host_objs, _field__type__map={"bk_host_id": int})
        _check_objs_fields_type(_objs=self.identity_data_objs, _field__type__map={"bk_host_id": int})


class AgentServiceBaseTestCase(CustomAPITestCase, ComponentTestMixin, ABC):

    # CustomAPITestCase
    LIST_SORT = True

    # DEBUG = True 时，会打印原子执行日志，帮助定位问题和确认执行步骤是否准确
    # ⚠️ 注意：请仅在本地开发机上使用，最后提交时，上层原子测试该值必须为 False
    DEBUG: bool = False

    OBJ_FACTORY_CLASS: Type[AgentTestObjFactory] = AgentTestObjFactory
    BATCH_CALL_MOCK_PATHS = [
        "apps.backend.components.collections.job.request_multi_thread",
        "apps.backend.components.collections.common.remote.concurrent.batch_call_coroutine",
    ]

    obj_factory: Optional[AgentTestObjFactory] = None
    # 原子的公共输入
    common_inputs: Dict[str, Any] = None

    @classmethod
    def setUpClass(cls):
        cls.obj_factory = cls.OBJ_FACTORY_CLASS()
        cls.setup_obj_factory()

        mock.patch.object(ConcurrentController, "batch_call_func", concurrent.batch_call_serial).start()

        # 多线程会影响测试debug，全局mock多线程执行，改为串行
        for batch_call_mock_path in cls.BATCH_CALL_MOCK_PATHS:
            mock.patch(batch_call_mock_path, concurrent.batch_call_serial).start()

        agent_dir_path = os.path.dirname(agent_new.__file__)
        relative_dir_path = agent_dir_path.replace(settings.BASE_DIR + os.path.sep, "")
        for file_name in os.listdir(agent_dir_path):
            if not (os.path.isfile(os.path.join(agent_dir_path, file_name)) or file_name.endswith(".py")):
                continue
            module_name = file_name[:-3]
            if module_name in ["__init__"]:
                continue
            for child_path in ["concurrent.batch_call_coroutine", "concurrent.batch_call"]:
                batch_call_mock_path = ".".join([relative_dir_path.replace(os.path.sep, "."), module_name, child_path])
                try:
                    mock.patch(batch_call_mock_path, concurrent.batch_call_serial).start()
                except (ModuleNotFoundError, AttributeError):
                    pass

        super().setUpClass()

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        pass

    @classmethod
    def setUpTestData(cls):
        cls.obj_factory.init_db()
        super().setUpTestData()

    def create_install_channel(self):
        """创建安装通道"""
        install_channel = models.InstallChannel.objects.create(
            bk_cloud_id=constants.DEFAULT_CLOUD,
            jump_servers=[common_unit.host.PROXY_INNER_IP],
            upstream_servers={
                "taskserver": [utils.DEFAULT_IP],
                "btfileserver": [utils.DEFAULT_IP],
                "dataserver": [utils.DEFAULT_IP],
                "agent_download_proxy": True,
                "channel_proxy_address": f"http://{utils.DEFAULT_IP}:17981",
            },
        )
        jump_server_host_id = self.obj_factory.RANDOM_BEGIN_HOST_ID + len(self.obj_factory.bk_host_ids) + 1
        jump_server = copy.deepcopy(common_unit.host.HOST_MODEL_DATA)
        jump_server.update(
            {
                "install_channel_id": install_channel.id,
                "bk_host_id": jump_server_host_id,
                "inner_ip": common_unit.host.PROXY_INNER_IP,
            }
        )
        proc_status_data = copy.deepcopy(common_unit.host.PROCESS_STATUS_MODEL_DATA)
        proc_status_data.update(
            {
                "bk_host_id": jump_server_host_id,
                "status": constants.ProcStateType.RUNNING,
                "proc_type": constants.ProcType.AGENT,
            }
        )
        self.obj_factory.bulk_create_model(model=models.Host, create_data_list=[jump_server])
        self.obj_factory.bulk_create_model(model=models.ProcessStatus, create_data_list=[proc_status_data])
        return install_channel

    @classmethod
    def create_ap(cls, name: str, description: str) -> models.AccessPoint:
        # 创建一个测试接入点
        ap_model_data = basic.remove_keys_from_dict(origin_data=common_unit.host.AP_MODEL_DATA, keys=["id"])
        ap_model_data.update({"name": name, "description": description, "is_default": False, "is_enabled": True})
        ap_obj = models.AccessPoint(**ap_model_data)
        ap_obj.save()
        return ap_obj

    def init_alive_proxies(self, bk_cloud_id: int):

        ap_obj = self.create_ap(name="Proxy专用接入点", description="用于测试PAgent是否正确通过存活Proxy获取到接入点")
        self.except_ap_ids = [ap_obj.id]

        proxy_host_ids = []
        proxy_data_host_list = []
        proc_status_data_list = []
        init_proxy_num = random.randint(5, 10)
        random_begin_host_id = self.obj_factory.RANDOM_BEGIN_HOST_ID + len(self.obj_factory.bk_host_ids) + 1

        for index in range(init_proxy_num):
            proxy_host_id = random_begin_host_id + index
            proxy_host_ids.append(proxy_host_id)
            proxy_data = copy.deepcopy(common_unit.host.HOST_MODEL_DATA)
            proxy_data.update(
                {
                    "ap_id": ap_obj.id,
                    "bk_cloud_id": bk_cloud_id,
                    "node_type": constants.NodeType.PROXY,
                    "bk_host_id": proxy_host_id,
                    "inner_ip": common_unit.host.PROXY_INNER_IP,
                }
            )
            proc_status_data = copy.deepcopy(common_unit.host.PROCESS_STATUS_MODEL_DATA)
            proc_status_data.update(
                {
                    "bk_host_id": proxy_host_id,
                    "status": constants.ProcStateType.RUNNING,
                    "proc_type": constants.ProcType.AGENT,
                }
            )
            proxy_data_host_list.append(proxy_data)
            proc_status_data_list.append(proc_status_data)
        self.obj_factory.bulk_create_model(model=models.Host, create_data_list=proxy_data_host_list)
        self.obj_factory.bulk_create_model(model=models.ProcessStatus, create_data_list=proc_status_data_list)

    def structure_common_inputs(self) -> Dict[str, Any]:
        """
        构造原子的公共输入，基础的输入数据对标 apps/backend/components/collections/base.py inputs_format
        :return:
        """
        subscription_step_id = self.obj_factory.sub_step_objs[0].id
        subscription_instance_ids = [sub_inst_obj.id for sub_inst_obj in self.obj_factory.sub_inst_record_objs]
        return {
            "blueking_language": get_language(),
            "act_name": self.component_cls().name,
            "subscription_step_id": subscription_step_id,
            "subscription_instance_ids": subscription_instance_ids,
        }

    def setUp(self) -> None:
        self.common_inputs = self.structure_common_inputs()
        super().setUp()

    def print_debug_log(self):
        if not self.DEBUG:
            return

        sub_inst_id__status_detail_obj_map: Dict[int, models.SubscriptionInstanceStatusDetail] = {}
        sub_inst_status_detail_objs = models.SubscriptionInstanceStatusDetail.objects.filter(
            subscription_instance_record_id__in=self.common_inputs["subscription_instance_ids"]
        ).all()
        for sub_inst_status_detail_obj in sub_inst_status_detail_objs:
            sub_inst_id = sub_inst_status_detail_obj.subscription_instance_record_id
            sub_inst_id__status_detail_obj_map[sub_inst_id] = sub_inst_status_detail_obj

        for sub_inst_obj in self.obj_factory.sub_inst_record_objs:
            print(f"sub_inst_id -> {sub_inst_obj.id} | ip -> {sub_inst_obj.instance_info['host']['bk_host_innerip']}")
            sub_inst_status_detail_obj = sub_inst_id__status_detail_obj_map.get(sub_inst_obj.id)
            if sub_inst_status_detail_obj is None:
                log = "There is no SubscriptionInstanceStatusDetail"
            else:
                log = sub_inst_status_detail_obj.log
            # 多行缩进，参考：https://stackoverflow.com/questions/8234274/
            print(textwrap.indent(log, 4 * " "))

    def tearDown(self) -> None:
        self.print_debug_log()
        super().tearDown()

    def _test_fail(self):
        # 打印错误日志
        self.print_debug_log()
        super()._test_fail()
