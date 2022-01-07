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


import abc
import copy
import time

import six
from django.utils.translation import ugettext as _

from apps.component.esbclient import client_v2
from apps.node_man.handlers.healthz.constants import CheckerStatus
from apps.node_man.handlers.healthz.healthz_test import (
    cc_test_cases,
    gse_test_cases,
    job_test_cases,
    nodeman_test_cases,
)
from apps.node_man.handlers.healthz.utils.thread import ThreadPool
from apps.utils.local import get_request
from common.api import GseApi, JobApi, NodeApi
from common.log import logger


def deep_parsing_metric_info(metric_info):
    parent_value = metric_info["result"]
    value_list = parent_value["value"]
    for item in value_list:
        if not isinstance(item, dict):
            raise TypeError
        sub_metric_info = copy.deepcopy(metric_info)
        name = item.pop("name", parent_value["name"])
        value = item.pop("value", "")
        status = item.pop("status", parent_value["status"])
        message = item.pop("message", parent_value["message"])
        if not message:
            message = " ".join(["{}: {}".format(k, v) for k, v in list(item.items())])
        sub_metric_info["result"] = {
            "name": name,
            "value": value,
            "message": message,
            "status": status,
        }
        if "description" in sub_metric_info:
            sub_metric_info["description"] += name
        else:
            sub_metric_info["description"] = name
        yield sub_metric_info


def monitor_time_elapsed(func):
    """
    用于监听函数运行时间的装饰器
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.debug(f"the function {func.__name__} starts")
        result = func(*args, **kwargs)
        logger.debug(f"the function {func.__name__} ends")
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(f"the function {func.__name__} takes {elapsed_time} seconds")
        return result

    return wrapper


class BaseHealthzChecker(six.with_metaclass(abc.ABCMeta, object)):
    """
    healthz checker的基类，其他的 checker 只需要继承自此类，然后将 name 和 category 赋值，并且实现 check 方法即可
    如果 checker 本身具有 solution ，则直接直接在 checker 中给出自身的 solution 即可
    如果 checker 有自定义的 clean 方法，可以先调用父类的 clean 方法，然后自定义其返回值即可
    """

    @abc.abstractproperty
    def name(self):
        raise NotImplementedError

    @abc.abstractmethod
    def check(self):
        raise NotImplementedError

    @abc.abstractmethod
    def category(self):
        raise NotImplementedError

    def __init__(self):
        self._api_list = []

    def clean_data(self):
        """
        用于清洗数据，给前端返回
        :return: data，清洗过后的数据
        """
        is_ok, details = self.check()
        data = {
            "collect_args": "{}",
            "solution": ((_("第三方组件%s异常") % self.name, _("请检查esb及对应组件服务是否正常")),),
            "result": {"status": 2, "message": "", "name": "", "value": None},
            "server_ip": "",
            "node_name": self.name,
            "description": self.name + _("状态"),
            "category": self.category,
            "collect_metric": self.name + ".status",
            "collect_type": "saas",
            "metric_alias": self.name + ".status",
        }
        data["result"] = {
            "status": CheckerStatus.CHECKER_OK if is_ok else CheckerStatus.CHECKER_FAILED,
            "message": details,
            "name": data["metric_alias"],
            "value": None,
        }
        data["solution"] = [
            {"reason": reason, "solution": solution} for reason, solution in getattr(self, "solution", data["solution"])
        ]
        return data

    def _find_children_list_of_api(self, api_name, test_cases):
        """
        查找依赖于 api_name 的接口
        :param api_name:
        :return:
        """
        for api_item, params in six.iteritems(test_cases):
            if api_name in params.get("dependencies", []):
                yield api_item, params["description"], params["args"]

    def _fill_self_api_list(self, test_cases):
        """
        解析 cc_test_cases 用于填充 api_list
        :return:
        """
        # 读取 cc_test_cases 将根 api 的 args 和其对应的子 api ，并填充到 api_list 中
        for base_api in test_cases:
            # 解析根接口
            if len(test_cases[base_api]["dependencies"]) == 0:
                self._api_list.append(
                    {
                        "api_name": base_api,
                        "description": _(test_cases[base_api]["description"]),
                        "children_api_list": [],
                        "results": {},
                        "args": test_cases[base_api]["args"],
                    }
                )
        # 根据依赖读取子接口
        for root_api in self._api_list:
            for child_api in self._find_children_list_of_api(root_api["api_name"], test_cases):
                root_api["children_api_list"].append(
                    {"api_name": child_api[0], "description": _(child_api[1]), "args": child_api[2], "results": {}}
                )


class CcHealthzChecker(BaseHealthzChecker):
    name = "cmdb"
    category = "esb"

    def check(self):
        """
        检查 cc_test_cases 是否为空
        :return:
        """
        if not cc_test_cases:
            return False, _("{} 不存在对应的测试用例".format(self.name))
        return True, "OK"

    @monitor_time_elapsed
    def clean_data(self):
        clean_data = super(CcHealthzChecker, self).clean_data()
        self._fill_self_api_list(cc_test_cases)
        clean_data["result"]["api_list"] = self._api_list
        return clean_data

    def test_root_api(self, method_name):
        """
        需要测试的根api名称
        :param method_name:
        :return:
        """
        request = get_request()
        # 获取到请求参数
        args = cc_test_cases.get(method_name, {}).get("args", None)
        if not args:
            args = {}
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        self._fill_self_api_list(cc_test_cases)
        if not any([i["api_name"] == method_name for i in self._api_list]):
            return False, method_name, _("cc中不存在{method_name}").format(method_name=method_name), args, {}
        method_func = getattr(client_v2.cc, method_name)
        try:
            result = method_func(args)
        except Exception as e:
            return False, method_name, str(e), args, {}
        return True, method_name, "OK", args, {"data": result}

    def test_non_root_api(self, api_name, parent_api, kwargs):
        """
        测试一个根api下的子api
        :param api_name: 要测试的api
        :param parent_api: 所依赖的api
        :param kwargs: 相关请求参数
        :return:
        """
        request = get_request()
        if parent_api not in cc_test_cases.get(api_name, {}).get("dependencies", []):
            return False, api_name, parent_api, _("接口不具有依赖关系"), kwargs, []
        method_func = getattr(client_v2.cc, api_name, None)
        if not method_func:
            return False, api_name, parent_api, _("cc中没有此接口"), kwargs, []
        # 默认测试数据为2
        args = {}
        if cc_test_cases[api_name].get("args", None):
            args = cc_test_cases[api_name]["args"]
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        if kwargs["data"]:
            args.update(kwargs["data"])

        try:
            result = method_func(args)
        except Exception as e:
            return False, api_name, parent_api, e, args, []
        return True, api_name, parent_api, "OK", args, list(result)


class NodemanHealthzChecker(BaseHealthzChecker):
    name = "nodeman"
    category = "esb"

    def check(self):
        """
        检查 nodeman_test_cases 是否为空
        :return:
        """
        if not nodeman_test_cases:
            return False, _("{} 不存在对应的测试用例".format(self.name))
        return True, "OK"

    @monitor_time_elapsed
    def clean_data(self):
        clean_data = super(NodemanHealthzChecker, self).clean_data()
        self._fill_self_api_list(nodeman_test_cases)
        clean_data["result"]["api_list"] = self._api_list
        return clean_data

    def test_root_api(self, method_name):
        """
        需要测试的根api名称
        :param method_name:
        :return:
        """
        request = get_request()
        # 获取到请求参数
        args = nodeman_test_cases.get(method_name, {}).get("args", None)
        if not args:
            args = {}
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        self._fill_self_api_list(nodeman_test_cases)
        if not any([i["api_name"] == method_name for i in self._api_list]):
            return False, method_name, _("cc中不存在{method_name}").format(method_name=method_name), args, {}
        method_func = getattr(NodeApi, method_name)
        try:
            result = method_func(args)
        except Exception as e:
            return False, method_name, str(e), args, {}
        return True, method_name, "OK", args, {"data": result}

    def test_non_root_api(self, api_name, parent_api, kwargs):
        """
        测试一个根api下的子api
        :param api_name: 要测试的api
        :param parent_api: 所依赖的api
        :param kwargs: 相关请求参数
        :return:
        """
        request = get_request()
        if parent_api not in nodeman_test_cases.get(api_name, {}).get("dependencies", []):
            return False, api_name, parent_api, _("接口不具有依赖关系"), kwargs, []
        method_func = getattr(NodeApi, api_name, None)
        if not method_func:
            return False, api_name, parent_api, _("cc中没有此接口"), kwargs, []
        # 默认测试数据为2
        args = {}
        if nodeman_test_cases[api_name].get("args", None):
            args = nodeman_test_cases[api_name]["args"]
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        if kwargs["data"]:
            args.update(kwargs["data"])

        try:
            result = method_func(args)
        except Exception as e:
            return False, api_name, parent_api, e, args, []
        return True, api_name, parent_api, "OK", args, list(result)


class GseHealthzChecker(BaseHealthzChecker):
    name = "gse"
    category = "esb"

    def check(self):
        """
        检查 gse_test_cases 是否为空
        :return:
        """
        if not gse_test_cases:
            return False, _("{} 不存在对应的测试用例".format(self.name))
        return True, "OK"

    @monitor_time_elapsed
    def clean_data(self):
        clean_data = super(GseHealthzChecker, self).clean_data()
        self._fill_self_api_list(gse_test_cases)
        clean_data["result"]["api_list"] = self._api_list
        return clean_data

    def test_root_api(self, method_name):
        """
        需要测试的根api名称
        :param method_name:
        :return:
        """
        request = get_request()
        # 获取到请求参数
        args = gse_test_cases.get(method_name, {}).get("args", None)
        if not args:
            args = {}
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        self._fill_self_api_list(gse_test_cases)
        if not any([i["api_name"] == method_name for i in self._api_list]):
            return False, method_name, _("cc中不存在{method_name}").format(method_name=method_name), args, {}
        method_func = getattr(GseApi, method_name)
        # 特殊处理
        if method_name == "get_agent_status":
            hosts_result = client_v2.cc.get_host_by_topo_node(bk_biz_id=args["bk_biz_id"])
            if hosts_result:
                host = hosts_result[0].bk_host_innerip
                bk_cloud_id = hosts_result[0].bk_cloud_id
                args.update({"hosts": [{"ip": host, "bk_cloud_id": bk_cloud_id}]})
        try:
            result = method_func(args)
        except Exception as e:
            return False, method_name, str(e), args, {}
        return True, method_name, "OK", args, {"data": result}

    def test_non_root_api(self, api_name, parent_api, kwargs):
        """
        测试一个根api下的子api
        :param api_name: 要测试的api
        :param parent_api: 所依赖的api
        :param kwargs: 相关请求参数
        :return:
        """
        request = get_request()
        if parent_api not in gse_test_cases.get(api_name, {}).get("dependencies", []):
            return False, api_name, parent_api, _("接口不具有依赖关系"), kwargs, []
        method_func = getattr(GseApi, api_name, None)
        if not method_func:
            return False, api_name, parent_api, _("cc中没有此接口"), kwargs, []
        # 默认测试数据为2
        args = {}
        if gse_test_cases[api_name].get("args", None):
            args = gse_test_cases[api_name]["args"]
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        if kwargs["data"]:
            args.update(kwargs["data"])

        try:
            result = method_func(args)
        except Exception as e:
            return False, api_name, parent_api, e, args, []
        return True, api_name, parent_api, "OK", args, list(result)


class MysqlHealthzChecker(BaseHealthzChecker):
    name = "mysql"
    category = "esb"

    def check(self):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()

        try:
            user_model.objects.filter(pk=1).exists()
        except Exception as e:
            return False, six.text_type(e)

        return True, "OK"


class JobHealthzChecker(BaseHealthzChecker):
    name = "job"
    category = "esb"

    def check(self):
        """
        检查 job_test_cases 是否为空
        :return:
        """
        if not job_test_cases:
            return False, _("job不存在对应的测试用例")
        # 检查是否存在 fast_execute_script 接口及其对应参数
        if not job_test_cases.get("fast_execute_script"):
            return False, _("job 中不存在接口 fast_execute_script 的相关参数")
        return True, "OK"

    @monitor_time_elapsed
    def clean_data(self):
        clean_data = super(JobHealthzChecker, self).clean_data()
        self._fill_self_api_list(job_test_cases)

        args = job_test_cases.get("fast_execute_script", {}).get("args", None)
        try:
            bk_biz_id = args["bk_biz_id"]
            hosts_result = client_v2.cc.get_host_by_topo_node(bk_biz_id=bk_biz_id)
            # 如果没有主机数据，则需要删除fast_execute_script接口
            if not hosts_result:
                for index, item in enumerate(self._api_list):
                    if item.get("api_name") == "fast_execute_script":
                        del self._api_list[index]
                        break
        except Exception:
            pass
        clean_data["result"]["api_list"] = self._api_list
        return clean_data

    def test_root_api(self, method_name):
        """
        需要测试的根api名称
        :param method_name:
        :return: status: 运行状态
                 api_name: 测试的根节点名称
                 message: 具体信息
                 args: 请求参数
                 result: 返回结果
        """
        # 获取到全局的request
        request = get_request()
        # 填充 self.api_list
        self._fill_self_api_list(job_test_cases)
        # 获取到请求参数
        args = job_test_cases.get(method_name, {}).get("args", None)
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        if not any([i["api_name"] == method_name for i in self._api_list]):
            return False, method_name, _("job中不存在{method_name}").format(method_name=method_name), args, {}
        method_func = getattr(JobApi, method_name)
        # 执行脚本
        if method_name == "fast_execute_script":
            # 通过app_id获取到host地址，然后取第一个用于测试
            try:
                hosts_result = client_v2.cc.get_host_by_topo_node(bk_biz_id=args["bk_biz_id"])
                if hosts_result:
                    host = hosts_result[0].bk_host_innerip
                    args.update({"ip": host, "ip_list": [{"ip": host, "bk_cloud_id": args["bk_cloud_id"]}]})
                else:
                    return False, method_name, _("查找业务下主机失败,主机查询结果:%s") % str(hosts_result), args, {}
            except Exception as e:
                return False, method_name, str(e), args, {}

        try:
            result = method_func(args)
        except Exception as e:
            return False, method_name, str(e), args, {}
        return True, method_name, "OK", args, {"data": result}

    def test_non_root_api(self, api_name, parent_api, kwargs):
        """
        测试一个根api下的子api
        :param api_name: 要测试的api
        :param parent_api: 所依赖的api
        :param kwargs: 相关请求参数
        :return:
        """
        # 获取到全局的request
        request = get_request()
        if parent_api not in job_test_cases.get(api_name, {}).get("dependencies", []):
            return False, api_name, parent_api, _("接口不具有依赖关系"), kwargs, []
        method_func = getattr(JobApi, api_name, None)
        if not method_func:
            return False, api_name, parent_api, _("job中没有此接口"), kwargs, []
        # 默认测试数据为2
        args = {}
        if job_test_cases[api_name].get("args", None):
            args = job_test_cases[api_name]["args"]
        if kwargs.get("data"):
            args.update(kwargs["data"])
        args.update({"bk_biz_id": request.biz_id, "operator": request.user.username})
        try:
            result = method_func(args)
        except Exception as e:
            return False, api_name, parent_api, str(e), args, []
        return True, api_name, parent_api, "OK", args, list(result)


@monitor_time_elapsed
def get_saas_healthz():
    def do_checker(checker):
        return checker.clean_data()

    metric_infos = []

    pool = ThreadPool()
    results = pool.map_ignore_exception(
        do_checker,
        (
            CcHealthzChecker(),
            JobHealthzChecker(),
            NodemanHealthzChecker(),
            GseHealthzChecker(),
        ),
    )
    pool.close()
    pool.join()

    for result in results:
        if isinstance(result, list):
            metric_infos.extend(result)
        else:
            metric_infos.append(result)

    return metric_infos


deep_parsing_metric_info = monitor_time_elapsed(deep_parsing_metric_info)
