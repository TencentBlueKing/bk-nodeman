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
from concurrent.futures import ThreadPoolExecutor, as_completed

from blueapps.account.models import User
from django.conf import settings
from iam import IAM

from apps.component.esbclient import client_v2
from apps.node_man import constants as const
from apps.node_man.constants import IamActionType
from apps.node_man.exceptions import IamRequestException
from apps.node_man.models import AccessPoint, Cloud, GsePluginDesc, Subscription
from apps.utils import APIModel


class IamHandler(APIModel):
    """
    用户权限处理器
    """

    # CMDB业务关联操作
    cmdb_related_action_biz = [
        IamActionType.agent_view,
        IamActionType.agent_operate,
        IamActionType.proxy_operate,
        IamActionType.plugin_view,
        IamActionType.plugin_operate,
        IamActionType.strategy_create,
        IamActionType.strategy_view,
        IamActionType.task_history_view,
    ]

    if settings.USE_IAM:
        _iam = IAM(settings.APP_CODE, settings.SECRET_KEY, settings.BK_IAM_INNER_HOST, settings.BK_COMPONENT_API_URL)
    else:
        _iam = object

    def fetch_biz(self):
        """
        获取全部业务
        """

        result = [
            {"bk_biz_id": business["bk_biz_id"], "bk_biz_name": business["bk_biz_name"]}
            for business in client_v2.cc.search_business({"fields": ["bk_biz_id", "bk_biz_name"]}).get("info") or []
        ]
        result.insert(0, {"bk_biz_id": settings.BK_CMDB_RESOURCE_POOL_BIZ_ID, "bk_biz_name": "资源池"})
        return result

    def fetch_cretor(self, instance_type, username):
        """
        返回云区域创建者为用户的ids
        :param instance_type: 实例类型
        :param username: 用户名
        :return: 列表，云区域ID集合
        """

        if instance_type == "cloud":
            clouds = Cloud.objects.values("bk_cloud_id", "creator")
            return [cloud["bk_cloud_id"] for cloud in clouds if username in cloud["creator"]]
        elif instance_type == "ap":
            aps = AccessPoint.objects.values("id", "creator")
            return [ap["id"] for ap in aps if username in ap.get("creator", [])]
        else:
            return []

    def fetch_all_permission(self, instance_type):
        """
        返回某实例类型的全部权限
        :param instance_type: 实例类型
        :return: 实例id集合
        """

        if instance_type == "cloud":
            # 拥有所有云区域权限
            return list(Cloud.objects.all().values_list("bk_cloud_id", flat=True))
        elif instance_type in ["biz", "agent", "plugin", "proxy", "task"]:
            # 拥有所有业务权限
            return [business["bk_biz_id"] for business in self.fetch_biz()]
        elif instance_type == "ap":
            # 拥有所有接入点权限
            return list(AccessPoint.objects.all().values_list("id", flat=True))
        elif instance_type == "package":
            # 拥有所有插件包权限
            return list(GsePluginDesc.objects.filter(category=const.CategoryType.official).values_list("id", flat=True))
        elif instance_type == "strategy":
            # 拥有所有策略权限
            return list(
                Subscription.objects.filter(category=Subscription.CategoryType.POLICY, is_deleted=False).values_list(
                    "id", flat=True
                )
            )
        else:
            return []

    def nodeman_policy_query(self, request_data):
        """
        封装policy_query接口
        :param: request_data: 请求参数
        """

        ok, message, temp_result = self._iam._client.policy_query(request_data)
        return ok, message, temp_result, request_data["action"]["id"]

    def handle_policy_content(self, content, action_id, instance_type, username, ret):
        """
        处理策略内容
        :param content: 权限策略
        :param action_id: 操作ID
        :param instance_type: 实例类型
        :param username: 用户名
        :param ret: 返回结果
        :return:
        """

        # 拥有全部权限
        if content["op"] == "any":
            if action_id in [
                IamActionType.globe_task_config,
                IamActionType.ap_create,
                IamActionType.cloud_create,
                IamActionType.plugin_pkg_import,
            ]:
                # 若是不关联实例的操作
                ret[action_id] = True
            else:
                ret[action_id] = self.fetch_all_permission(instance_type)

        # 拥有单个权限
        elif content["field"] in ["biz.id", "cloud.id", "ap.id", "strategy.id", "package.id"] and content["op"] == "eq":
            ret[action_id].append(int(content["value"]))

        # 拥有部分权限
        elif content["field"] in ["biz.id", "cloud.id", "ap.id", "strategy.id", "package.id"] and content["op"] == "in":
            ret[action_id].extend([int(value) for value in content["value"]])

        # 创建者，拥有其关联的权限
        elif (
            content["field"] == instance_type + ".iam_resource_owner"
            and content["op"] == "eq"
            and content["value"] == username
        ):
            ret[action_id] = self.fetch_cretor(instance_type, username)
        return ret

    def fetch_policy(self, username, actions):
        """
        向权限中心查询用户权限
        :param actions: 批量的操作ID
        """
        ret = {}
        is_superuser = IamHandler.is_superuser(username)
        if not settings.USE_IAM:
            # 没有使用权限中心，走老版本权限控制
            for action in actions:
                # 接入点方面
                if (
                    action
                    in [IamActionType.ap_edit, IamActionType.ap_delete, IamActionType.ap_create, IamActionType.ap_view]
                    and is_superuser
                ):
                    ret[action] = list(AccessPoint.objects.values_list("id", flat=True))

                # 云区域方面
                elif action in [
                    IamActionType.cloud_view,
                    IamActionType.cloud_edit,
                    IamActionType.cloud_delete,
                    IamActionType.cloud_create,
                ]:
                    if is_superuser:
                        # 超管用户拥有所有权限
                        ret[action] = list(Cloud.objects.values_list("bk_cloud_id", flat=True))
                    else:
                        clouds = dict(Cloud.objects.all().values_list("bk_cloud_id", "creator"))
                        ret[action] = [cloud for cloud in clouds if username in clouds[cloud]]
                else:
                    ret[action] = []

            return ret

        # 超管不需要请求权限中心
        if is_superuser:
            for action_id in actions:
                instance_type = action_id.split("_")[0]
                action_type = action_id.split("_")[1]
                instance_type = self.get_instance_type(instance_type, action_type)
                ret[action_id] = []
                ret = self.handle_policy_content({"op": "any"}, action_id, instance_type, username, ret)
            return ret

        # 普通用户请求权限详情
        request_list = []
        result = []
        for action in actions:
            data = {
                "system": settings.BK_IAM_SYSTEM_ID,
                "subject": {"type": "user", "id": username},
                "action": {"id": action},
                "resources": [],
            }

            request_list.append(data)

        # 并发请求权限中心接口
        with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
            tasks = [ex.submit(self.nodeman_policy_query, request_data) for request_data in request_list]
            for future in as_completed(tasks):
                ok, message, temp_result, action_id = future.result()
                if not ok:
                    raise IamRequestException(message)
                result.append({"action": {"id": action_id}, "condition": temp_result})

        for action in result:
            action_id = action["action"]["id"]
            # instance_type = action_id.split("_")[0]
            instance_type = action_id.split("_")[0]
            action_type = action_id.split("_")[1]
            instance_type = self.get_instance_type(instance_type, action_type)
            ret[action_id] = []
            if action["condition"] and not action["condition"].get("content"):
                # 返回了单个实例的情况
                ret = self.handle_policy_content(action["condition"], action_id, instance_type, username, ret)

            elif action["condition"] and action["condition"].get("content"):
                # 返回了多个实例的情况，对于节点管理，只有OR的情况
                for instance in action["condition"]["content"]:
                    ret = self.handle_policy_content(instance, action_id, instance_type, username, ret)
            else:
                # 没有权限
                if action_id in [
                    IamActionType.globe_task_config,
                    IamActionType.ap_create,
                    IamActionType.cloud_create,
                    IamActionType.plugin_pkg_import,
                ]:
                    ret[action_id] = False
                else:
                    ret[action_id] = []

        return ret

    @staticmethod
    def get_instance_type(instance_type, action_type):
        if instance_type in ["plugin"] and action_type == "pkg":
            instance_type = "package"

        elif instance_type in ["agent", "proxy", "task", "plugin"]:
            instance_type = "biz"

        elif instance_type == "strategy" and action_type in ["create", "view"]:
            instance_type = "biz"

        return instance_type

    def fetch_redirect_url(self, params, username):
        """
        返回跳转链接
        :param params: 参数
        :param username: 用户名
        :return:
        """

        no_related_resource_actions = [IamActionType.plugin_pkg_import]

        data = {"system_id": settings.BK_IAM_SYSTEM_ID, "actions": []}
        action_map = {}
        for info in params:
            if info["action"] in action_map:
                action_map[info["action"]].append(info)
            else:
                action_map[info["action"]] = [info]

        for action, resources in action_map.items():
            if action in no_related_resource_actions:
                apply_info = {"id": action}
            else:
                apply_info = {"id": action, "related_resource_types": []}  # 操作id
                instance_type = action.split("_")[0]
                action_type = action.split("_")[1]

                if action_type != "create" or action == "strategy_create":
                    action_type = self.get_instance_type(instance_type, action_type)
                    if action in self.cmdb_related_action_biz:
                        system_id = settings.BK_IAM_CMDB_SYSTEM_ID
                    else:
                        system_id = settings.BK_IAM_SYSTEM_ID

                    apply_info["related_resource_types"].append(
                        {
                            # 关联的资源类型, 无关联资源类型的操作, 可以为空
                            "system_id": system_id,
                            "type": action_type,
                        }
                    )
                    instances = []

                    for param in resources:
                        instance_id = param.get("instance_id")
                        instance_name = param.get("instance_name")
                        if instance_id:
                            instances.append(
                                [
                                    {
                                        # 层级节点的资源类型
                                        "type": action_type,
                                        "id": instance_id,  # 层级节点的资源实例id
                                        "name": instance_name,  # 层级节点的资源名称
                                    }
                                ]
                            )
                    if instances:
                        apply_info["related_resource_types"][0]["instances"] = instances
            data["actions"].append(apply_info)
        ok, message, result = IamHandler._iam._client.get_apply_url(bk_token="", bk_username=username, data=data)
        return result or settings.BK_IAM_SAAS_HOST

    @staticmethod
    def return_resource_instance_creator(resource_id, instance_id, instance_name, creator):
        """
        返回创建者给权限中心
        :param resource_id: 资源ID
        :param instance_id: 实例ID
        :param instance_name: 实例名称
        :param creator: 创建者
        """

        data = {
            "system": settings.BK_IAM_SYSTEM_ID,
            "type": resource_id,
            "id": instance_id,
            "name": instance_name,
            "creator": creator,
        }
        ok, message = IamHandler._iam._client.grant_resource_creator_actions(
            bk_token="", bk_username=creator, data=data
        )
        return ok, message

    @staticmethod
    def sync_cloud_instance(instance_id, instance_name, creator):
        """
        迁移云区域数据时使用的接口
        :param instance_id: 实例ID
        :param instance_name: 实例名称
        :param creator: 创建者
        """

        data = {
            "system": settings.BK_IAM_SYSTEM_ID,
            "asynchronous": False,
            "operate": "grant",
            "actions": [  # 批量的操作
                {"id": IamActionType.cloud_view},
                {"id": IamActionType.cloud_edit},
                {"id": IamActionType.cloud_delete},
            ],
            "subject": {"type": "user", "id": creator},
            "resources": [
                {  # 操作关联的资源类型, 必须与所有的actions都匹配
                    "system": settings.BK_IAM_SYSTEM_ID,
                    "type": "cloud",
                    "instances": [{"id": instance_id, "name": instance_name}],  # 批量资源实例
                }
            ],
        }
        ok, message = IamHandler._iam._client.grant_batch_instance(bk_token="", bk_username=creator, data=data)
        return ok, message

    @staticmethod
    def is_superuser(username) -> bool:
        """
        是否为超管
        :param username: 用户名
        :return: 是否为超管
        """

        # TODO: 等待权限中心用户组注册功能上线
        # return iam.is_superuser
        is_superuser = User.objects.filter(username=username, is_superuser=True).exists()
        return is_superuser

    @staticmethod
    def iam_global_settings_permission(username) -> bool:
        """
        是否有全局配置权限
        :param username: 用户名
        :return True/False 是否有权限
        """

        if settings.USE_IAM:
            # 是否使用权限中心
            permissions = IamHandler().fetch_policy(
                username,
                [
                    IamActionType.ap_view,
                    IamActionType.ap_edit,
                    IamActionType.ap_delete,
                    IamActionType.ap_create,
                    IamActionType.globe_task_config,
                ],
            )
        else:
            permissions = []

        is_visible = False
        for action in permissions:
            if permissions[action]:
                is_visible = True

        # 是否超管
        if IamHandler.is_superuser(username):
            is_visible = True

        return is_visible

    @staticmethod
    def globe_task_config(username):
        """
        任务配置权限
        """

        if IamHandler.is_superuser(username):
            # 是否超管
            return True
        if settings.USE_IAM:
            # 是否使用权限中心
            result = IamHandler().fetch_policy(username, [IamActionType.globe_task_config])[
                IamActionType.globe_task_config
            ]
            if result:
                return True
            else:
                return False
        else:
            return False
