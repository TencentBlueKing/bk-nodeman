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
from unittest.mock import patch

from django.test import TestCase

from apps.node_man import constants as const
from apps.node_man.exceptions import (
    ApIDNotExistsError,
    BusinessNotPermissionError,
    CloudNotExistError,
    CloudNotPermissionError,
    IpRunningJob,
    NotExistsOs,
    ProxyNotAvaliableError,
)
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.validator import (
    bulk_update_validate,
    job_validate,
    operate_validator,
    update_pwd_validate,
)
from apps.node_man.models import Host, IdentityData
from apps.node_man.tests.utils import (
    MockClient,
    cmdb_or_cache_biz,
    create_cloud_area,
    create_host,
    gen_job_data,
    gen_update_accept_list,
    ret_to_validate_data,
)


class TestValidator(TestCase):
    @staticmethod
    def wrap_job_validate(data, task_info=None):
        if task_info is None:
            task_info = {}
        # 封装数据生成和job_validate，减少重复代码
        (
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            all_outer_ip_info,
            all_login_ip_info,
            bk_biz_scope,
        ) = ret_to_validate_data(data)

        ip_filter_list, accept_list, proxy_not_alive = job_validate(
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            bk_biz_scope,
            task_info,
            "admin",
            True,
            "ticket",
        )
        return ip_filter_list, accept_list

    def wrap_job_validate_raise(self, data, username, is_superuser, error, task_info=None):
        """
        封装job_validate测试异常抛出通用逻辑
        :param data:
        :param username:
        :param is_superuser:
        :param error:
        :param task_info:
        :return:
        data:
        {
          "job_type": "INSTALL_PROXY",
          "op_type": "INSTALL",
          "node_type": "PROXY",
          "hosts": [
            {
              "bk_cloud_id": 1,
              "ap_id": -1,
              "bk_biz_id": 31,
              "os_type": "LINUX",
              "inner_ip": "127.0.0.1",
              "outer_ip": "127.0.0.1",
              "login_ip": "127.0.0.1",
              "account": "root",
              "port": 0,
              "bk_biz_scope": [27],
              "auth_type": "PASSWORD",
              "password": "0",
              "is_manual": false
            }
          ]
        }
        """
        if task_info is None:
            task_info = {}
        (
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            all_outer_ip_info,
            all_login_ip_info,
            bk_biz_scope,
        ) = ret_to_validate_data(data)

        self.assertRaises(
            error,
            job_validate,
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            bk_biz_scope,
            task_info,
            username,
            is_superuser,
            "ticket",
        )

    @staticmethod
    def wrap_update_pwd_validate(host_to_create, identity_to_create, no_change):

        accept_list = gen_update_accept_list(host_to_create, identity_to_create, no_change=no_change)
        identity_info = {
            identity["bk_host_id"]: {
                "auth_type": identity["auth_type"],
                "retention": identity["retention"],
                "account": identity["account"],
                "password": identity["password"],
                "key": identity["key"],
                "port": identity["port"],
                "extra_data": identity["extra_data"],
            }
            for identity in IdentityData.objects.filter(
                bk_host_id__in=[host["bk_host_id"] for host in accept_list]
            ).values("bk_host_id", "auth_type", "retention", "account", "password", "key", "port", "extra_data")
        }
        return accept_list, identity_info

    @staticmethod
    def wrap_special_pwd_validate(host_to_create, identity_to_create, auth_type, ip=False):
        accept_list = [
            {
                "bk_host_id": host_to_create[i].bk_host_id,
                "account": identity_to_create[i].account,
                "inner_ip": None if ip is False else host_to_create[i].inner_ip,
                "port": identity_to_create[i].port,
                "auth_type": auth_type,
            }
            for i in range(len(host_to_create))
        ]
        identity_info = {
            identity["bk_host_id"]: {
                "auth_type": identity["auth_type"],
                "retention": identity["retention"],
                "account": identity["account"],
                "password": identity["password"],
                "key": identity["key"],
                "port": identity["port"],
                "extra_data": identity["extra_data"],
            }
            for identity in IdentityData.objects.filter(
                bk_host_id__in=[host["bk_host_id"] for host in accept_list]
            ).values("bk_host_id", "auth_type", "retention", "account", "password", "key", "port", "extra_data")
        }
        return accept_list, identity_info

    def _test_job_validate_success(self):
        # 正常校验
        create_cloud_area(100)
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_PROXY, count=number, ap_id=const.DEFAULT_AP_ID)
        ip_filter_list, accept_list = self.wrap_job_validate(data)
        self.assertEquals(number, len(ip_filter_list) + len(accept_list))

    def _test_job_validate_os_not_exists(self):
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_AGENT, count=number, bk_cloud_id=0, bk_biz_id=27)
        data["hosts"][0]["os_type"] = None
        self.wrap_job_validate_raise(data, "admin", True, NotExistsOs)

    def _test_job_validate_not_biz_permission(self):
        # 用户不具有业务的权限
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_PROXY, count=number, bk_cloud_id=1, bk_biz_id=2123)
        self.wrap_job_validate_raise(data, "test", False, BusinessNotPermissionError)

    def _test_job_validate_cloud_not_exists(self):
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_AGENT, count=number, bk_cloud_id=99, bk_biz_id=27)
        (
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            all_outer_ip_info,
            all_login_ip_info,
            bk_biz_scope,
        ) = ret_to_validate_data(data)

        # 移除一个云区域
        cloud_info.pop(99)
        self.assertRaises(
            CloudNotExistError,
            job_validate,
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            bk_biz_scope,
            {},
            "test",
            False,
            "ticket",
        )

    def _test_job_validate_not_cloud_permission(self):
        # 是否有云区域权限
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_PROXY, count=number, bk_cloud_id=99, bk_biz_id=27)
        self.wrap_job_validate_raise(data, "test", False, CloudNotPermissionError)

    def _test_job_validate_proxy_not_available(self):
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_PROXY, count=number, bk_cloud_id=const.DEFAULT_CLOUD)
        self.wrap_job_validate_raise(data, "test", False, ProxyNotAvaliableError)

    def _test_job_validate_proxy_not_alive(self):
        # 测试P-Agent代理不可用
        # 非直连区域下，并且
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_AGENT, count=number, bk_cloud_id=99)

        (
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            all_outer_ip_info,
            all_login_ip_info,
            bk_biz_scope,
        ) = ret_to_validate_data(data)
        _, _, proxy_not_alive = job_validate(
            biz_info,
            data,
            cloud_info,
            ap_id_name,
            all_inner_ip_info,
            bk_biz_scope,
            {},
            "admin",
            True,
            "ticket",
        )
        self.assertEqual(len(proxy_not_alive), 1)

    def _test_job_validate_ap_id_not_exists(self):
        # 直连区域必须填写Ap_id
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_AGENT, count=number, bk_cloud_id=const.DEFAULT_CLOUD)
        # 接入点置空
        data["hosts"][0]["ap_id"] = None
        self.wrap_job_validate_raise(data, "admin", True, ApIDNotExistsError)

    def _test_job_validate_ap_id_not_match(self):

        # 直连区域必须填写Ap_id
        number = 1
        data = gen_job_data(job_type=const.JobType.INSTALL_AGENT, count=number, bk_cloud_id=1)
        # 创建一个可用的代理
        create_host(number=1, bk_cloud_id=1, bk_host_id=8888, node_type="PROXY")
        # 修改接入点为异常情况
        data["hosts"][0]["ap_id"] = 333
        self.wrap_job_validate_raise(data, "admin", True, ApIDNotExistsError)

    def _test_job_validate_ap_id_not_in_db(self):
        # 判断参数AP_ID是否存在在数据库中
        number = 1
        data = gen_job_data(
            job_type=const.JobType.INSTALL_AGENT, count=number, bk_cloud_id=const.DEFAULT_CLOUD, ap_id=100
        )
        self.wrap_job_validate_raise(data, "admin", True, ApIDNotExistsError)

    def _test_job_validate_inner_ip_had_exists(self):
        # ip是否已被占用, 内网，目前已解除内网ip限制
        number = 0
        create_host(number=1, bk_cloud_id=1, bk_host_id=9000, ip="255.255.255.1", node_type="PROXY")
        data = gen_job_data(
            job_type=const.JobType.INSTALL_PROXY,
            count=number,
            bk_cloud_id=1,
            ap_id=const.DEFAULT_AP_ID,
            ip="255.255.255.1",
        )
        ip_filter_list, accept_list = self.wrap_job_validate(data)
        self.assertEquals(number, len(ip_filter_list))

    def _test_job_validate_inner_ip_had_exists_other_op(self):
        number = 1
        bk_host_id = 9003
        inner_ip = "255.255.255.4"
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=bk_host_id, ip=inner_ip, node_type="AGENT", bk_cloud_id=1
        )
        data = gen_job_data(
            job_type=const.JobType.RESTART_AGENT,
            count=number,
            bk_cloud_id=1,
            ap_id=const.DEFAULT_AP_ID,
            ip="255.255.255.5",
            host_to_create=host_to_create,
            identity_to_create=identity_to_create,
        )
        ip_filter_list, accept_list = self.wrap_job_validate(data)
        self.assertEquals(number, len(ip_filter_list))

        # 除安装操作外，其他操作时检测Host ID是否正确
        number = 1
        data = gen_job_data(
            job_type=const.JobType.RESTART_AGENT,
            count=number,
            bk_cloud_id=1,
            ap_id=const.DEFAULT_AP_ID,
            ip=inner_ip,
            host_to_create=host_to_create,
            identity_to_create=identity_to_create,
            bk_host_id=999999,
        )
        ip_filter_list, accept_list = self.wrap_job_validate(data)
        self.assertEquals(number, len(ip_filter_list))

        # 除安装操作外，该Host是否正在执行任务
        number = 1
        data = gen_job_data(
            job_type=const.JobType.RESTART_AGENT,
            count=number,
            bk_cloud_id=1,
            ap_id=const.DEFAULT_AP_ID,
            ip=inner_ip,
            host_to_create=host_to_create,
            identity_to_create=identity_to_create,
        )

        ip_filter_list, accept_list = self.wrap_job_validate(data, task_info={bk_host_id: {"status": "RUNNING"}})

        self.assertEquals(number, len(ip_filter_list))

    def _test_job_validate_install_type_not_consistent(self):
        number = 1
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9005, ip="255.255.255.6", node_type="AGENT", bk_cloud_id=1
        )

        data = gen_job_data(
            job_type=const.JobType.RESTART_PROXY,
            count=number,
            bk_cloud_id=1,
            ap_id=const.DEFAULT_AP_ID,
            ip="255.255.255.6",
            host_to_create=host_to_create,
            identity_to_create=identity_to_create,
        )

        ip_filter_list, accept_list = self.wrap_job_validate(data)

        self.assertEquals(number, len(ip_filter_list))

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_validate(self):
        # 测试正常校验
        self._test_job_validate_success()
        # 测试操作系统不存在
        self._test_job_validate_os_not_exists()
        # 测试业务不存在
        self._test_job_validate_not_biz_permission()
        # 测试云区域不存在
        self._test_job_validate_cloud_not_exists()
        # 测试无云区域权限
        self._test_job_validate_not_cloud_permission()
        # 测试直连区域下不允许安装Proxy
        self._test_job_validate_proxy_not_available()
        # PAGENT的情况下，该云区域下是否有可用PROXY
        self._test_job_validate_proxy_not_alive()
        # 测试直连区域必须填写Ap_id
        self._test_job_validate_ap_id_not_exists()
        # 测试ap_id不一致
        self._test_job_validate_ap_id_not_match()
        # 判断参数AP_ID是否存在在数据库中
        self._test_job_validate_ap_id_not_in_db()
        # 测试内网ip占用
        self._test_job_validate_inner_ip_had_exists()
        # 安装操作外，其他操作时内网IP是否存在
        self._test_job_validate_inner_ip_had_exists_other_op()
        # 节点类型是否与操作类型一致, 如本身为PROXY，重装却为AGENT
        self._test_job_validate_install_type_not_consistent()

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_update_pwd_validate(self):

        create_cloud_area(100)

        # 不做任何修改
        host_to_create, _, identity_to_create = create_host(
            number=1,
            bk_host_id=9001,
            ip="255.255.255.1",
            node_type="AGENT",
            bk_cloud_id=1,
            upstream_nodes=[],
            outer_ip="255.255.255.1",
            login_ip="255.255.255.1",
            proc_type="AGENT",
            auth_type="PASSWORD",
        )

        accept_list, identity_info = self.wrap_update_pwd_validate(host_to_create, identity_to_create, no_change=True)
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(not_mod), 1)

        # 正常修改
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9002, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1
        )

        accept_list, identity_info = self.wrap_update_pwd_validate(host_to_create, identity_to_create, no_change=False)
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(mod), 1)

        # 修改authtype，但是没上传秘钥, 不带IP的（创建）
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9003, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1, auth_type="PASSWORD"
        )
        accept_list, identity_info = self.wrap_special_pwd_validate(host_to_create, identity_to_create, "KEY")
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(ip_filter_list), 1)

        # 修改authtype，但是没上传秘钥, 带IP的（更新）
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9004, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1, auth_type="PASSWORD"
        )
        accept_list, identity_info = self.wrap_special_pwd_validate(host_to_create, identity_to_create, "KEY", ip=True)
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(ip_filter_list), 1)

        # 修改authtype，但是没上传密码, 不带IP的（创建）
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9005, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1, auth_type="KEY"
        )
        accept_list, identity_info = self.wrap_special_pwd_validate(host_to_create, identity_to_create, "PASSWORD")
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(ip_filter_list), 1)

        # 修改authtype，但是没上传密码, 带IP的（更新）
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9006, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1, auth_type="KEY"
        )
        accept_list, identity_info = self.wrap_special_pwd_validate(
            host_to_create, identity_to_create, "PASSWORD", ip=True
        )
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(ip_filter_list), 1)

        # 修改authtype，但是上传了密码，正常通过校验
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9007, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1, auth_type="KEY"
        )
        accept_list, identity_info = self.wrap_special_pwd_validate(host_to_create, identity_to_create, "PASSWORD")
        accept_list[0]["PASSWORD"] = "zxcvczxvx"
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(ip_filter_list), 1)

        # 认证信息过期
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9008, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1, auth_type="PASSWORD"
        )

        # 设置密码、Key为空
        identity = IdentityData.objects.get(bk_host_id=9008)
        identity.key = None
        identity.password = None
        identity.save()

        accept_list, identity_info = self.wrap_special_pwd_validate(
            host_to_create, identity_to_create, "PASSWORD", ip=True
        )
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        self.assertEqual(len(ip_filter_list), 1)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_bulk_update_validate(self):
        create_cloud_area(100)

        # 不做任何修改
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9001, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1
        )

        accept_list, identity_info = self.wrap_update_pwd_validate(host_to_create, identity_to_create, no_change=True)
        host_info = {
            host["bk_host_id"]: host
            for host in Host.objects.filter(bk_host_id__in=[host["bk_host_id"] for host in accept_list]).values()
        }
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])
        result, _ = bulk_update_validate(host_info, accept_list, identity_info, ip_filter_list)
        self.assertEqual(len(result["not_modified_host"]), 1)

        # 正常修改
        host_to_create, _, identity_to_create = create_host(
            number=1, bk_host_id=9002, ip="255.255.255.1", node_type="AGENT", bk_cloud_id=1
        )

        accept_list, identity_info = self.wrap_update_pwd_validate(host_to_create, identity_to_create, no_change=False)
        host_info = {
            host["bk_host_id"]: host
            for host in Host.objects.filter(bk_host_id__in=[host["bk_host_id"] for host in accept_list]).values()
        }
        not_mod, mod, ip_filter_list = update_pwd_validate(accept_list, identity_info, [])

        result, _ = bulk_update_validate(host_info, accept_list, identity_info, ip_filter_list)
        self.assertEqual(len(result["modified_host"]), 1)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_operator_validate_not_exists_os(self):
        # 该主机是否有操作系统
        inner_ip = "1.1.1.1"
        bk_host_id = 1
        bk_cloud_id = 1
        node_type = "AGENT"
        create_cloud_area(1)
        create_host(number=1, bk_cloud_id=bk_cloud_id, bk_host_id=bk_host_id, ip=inner_ip, node_type=node_type)
        # 不传os_type参数即可
        db_host_sql = [
            {"inner_ip": inner_ip, "bk_host_id": bk_host_id, "bk_cloud_id": bk_cloud_id, "node_type": node_type}
        ]
        # 需测试权限中心时，params需要传递相关key:value参数
        user_biz = CmdbHandler().biz_id_name({})
        self.assertRaises(NotExistsOs, operate_validator, db_host_sql, user_biz, "admin", {}, True)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_operator_validate_not_biz_permission(self):
        # 该主机是否有操作系统
        inner_ip = "1.1.1.1"
        bk_host_id = 1
        bk_cloud_id = 1
        node_type = "AGENT"
        os_type = "LINUX"
        bk_biz_id = 2

        create_cloud_area(1)
        create_host(number=1, bk_cloud_id=bk_cloud_id, bk_host_id=bk_host_id, ip=inner_ip, node_type=node_type)
        # 是否有业务权限
        db_host_sql = [
            {
                "inner_ip": inner_ip,
                "bk_host_id": bk_host_id,
                "os_type": os_type,
                "bk_cloud_id": 0,
                "node_type": node_type,
                "bk_biz_id": bk_biz_id,
            }
        ]
        # 无权限测试
        user_biz = CmdbHandler().biz_id_name({})
        self.assertRaises(
            BusinessNotPermissionError, operate_validator, db_host_sql, user_biz, "special_test", {}, True
        )

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_operator_validate_cloud_not_exists(self):
        # 该主机是否有操作系统
        inner_ip = "1.1.1.1"
        bk_host_id = 1
        bk_cloud_id = 1
        node_type = "AGENT"
        os_type = "LINUX"
        bk_biz_id = 27

        create_cloud_area(1)
        create_host(number=1, bk_cloud_id=bk_cloud_id, bk_host_id=bk_host_id, ip=inner_ip, node_type=node_type)

        # 云区域是否存在
        db_host_sql = [
            {
                "inner_ip": inner_ip,
                "bk_host_id": bk_host_id,
                "os_type": os_type,
                "bk_cloud_id": 9999,
                "node_type": node_type,
                "bk_biz_id": bk_biz_id,
            }
        ]
        user_biz = CmdbHandler().biz_id_name({})

        self.assertRaises(CloudNotPermissionError, operate_validator, db_host_sql, user_biz, "admin", {}, True)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_operator_validate_ip_running_job(self):
        # 该主机是否有操作系统
        inner_ip = "1.1.1.1"
        bk_host_id = 1
        bk_cloud_id = 1
        node_type = "AGENT"
        os_type = "LINUX"
        bk_biz_id = 27

        # 创建一个代理
        create_host(number=1, bk_cloud_id=bk_cloud_id, bk_host_id=2, ip=inner_ip, node_type="PROXY")
        # 将密码设置为空
        identity = IdentityData.objects.get(bk_host_id=2)
        identity.password = None
        identity.key = None
        identity.save()
        # 测试
        db_host_sql = [
            {
                "inner_ip": inner_ip,
                "bk_host_id": bk_host_id,
                "os_type": os_type,
                "bk_cloud_id": 0,
                "node_type": node_type,
                "bk_biz_id": bk_biz_id,
            }
        ]
        user_biz = CmdbHandler().biz_id_name({})

        # 是否正在执行任务
        # 创建一个可用代理
        create_host(number=1, bk_cloud_id=bk_cloud_id, bk_host_id=3, ip=inner_ip, node_type="PROXY")
        self.assertRaises(
            IpRunningJob, operate_validator, db_host_sql, user_biz, "admin", {bk_host_id: {"status": "RUNNING"}}, True
        )
