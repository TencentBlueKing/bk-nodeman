# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from typing import Dict, List, Union

from django.conf import settings
from django.utils.translation import ugettext as _
from iam import IAM, DummyIAM, MultiActionRequest, Request, Resource, Subject
from iam.apply.models import (
    ActionWithoutResources,
    ActionWithResources,
    Application,
    RelatedResourceType,
    ResourceInstance,
    ResourceNode,
)
from iam.exceptions import AuthAPIError
from iam.meta import setup_action, setup_resource, setup_system
from iam.utils import gen_perms_apply_data

from apps.iam.exceptions import (
    ActionNotExistError,
    GetSystemInfoError,
    PermissionDeniedError,
)
from apps.iam.handlers.actions import ActionMeta, _all_actions, get_action_by_id
from apps.iam.handlers.resources import _all_resources, get_resource_by_id
from apps.utils.local import get_request
from common.log import logger


class Permission(object):
    """
    权限中心鉴权封装
    """

    def __init__(self, username: str = "", request=None):
        if username:
            self.username = username
            self.bk_token = ""
        else:
            try:
                request = request or get_request()
            except Exception:
                raise ValueError("must provide `username` or `request` param to init")

            self.bk_token = request.COOKIES.get("bk_token", "")
            self.username = request.user.username

        self.iam_client = self.get_iam_client()

    @classmethod
    def get_iam_client(cls):
        if settings.BK_IAM_SKIP:
            return DummyIAM(
                settings.APP_ID, settings.APP_TOKEN, settings.BK_IAM_INNER_HOST, settings.BK_PAAS_INNER_HOST
            )
        return IAM(settings.APP_ID, settings.APP_TOKEN, settings.BK_IAM_INNER_HOST, settings.BK_PAAS_INNER_HOST)

    def make_request(self, action: Union[ActionMeta, str], resources: List[Resource] = None) -> Request:
        """
        获取请求对象
        """
        action = get_action_by_id(action)
        resources = resources or []
        request = Request(
            system=settings.BK_IAM_SYSTEM_ID,
            subject=Subject("user", self.username),
            action=action,
            resources=resources,
            environment=None,
        )
        return request

    def make_multi_action_request(
        self, actions: List[Union[ActionMeta, str]], resources: List[Resource] = None
    ) -> MultiActionRequest:
        """
        获取多个动作请求对象
        """
        resources = resources or []
        actions = [get_action_by_id(action) for action in actions]
        request = MultiActionRequest(
            system=settings.BK_IAM_SYSTEM_ID,
            subject=Subject("user", self.username),
            actions=actions,
            resources=resources,
            environment=None,
        )
        return request

    def _make_application(
        self, action_ids: List[str], resources: List[Resource] = None, system_id: str = settings.BK_IAM_SYSTEM_ID
    ) -> Application:

        resources = resources or []
        actions = []

        for action_id in action_ids:
            # 对于没有关联资源的动作，则不传资源
            related_resources_types = []
            try:
                action = get_action_by_id(action_id)
                action_id = action.id
                related_resources_types = action.related_resource_types
            except ActionNotExistError:
                pass

            if not related_resources_types:
                actions.append(ActionWithoutResources(action_id))
            else:
                related_resources = []
                for related_resource in related_resources_types:
                    instances = []
                    for r in resources:
                        if r.system == related_resource.system_id and r.type == related_resource.id:
                            instances.append(
                                ResourceInstance(
                                    [ResourceNode(type=r.type, id=r.id, name=r.attribute.get("name", r.id))]
                                )
                            )

                    related_resources.append(
                        RelatedResourceType(
                            system_id=related_resource.system_id,
                            type=related_resource.id,
                            instances=instances,
                        )
                    )

                actions.append(ActionWithResources(action_id, related_resources))

        application = Application(system_id, actions=actions)
        return application

    def get_apply_url(
        self, action_ids: List[str], resources: List[Resource] = None, system_id: str = settings.BK_IAM_SYSTEM_ID
    ):
        """
        处理无权限 - 跳转申请列表
        """
        application = self._make_application(action_ids, resources, system_id)
        ok, message, url = self.iam_client.get_apply_url(application, self.bk_token, self.username)
        if not ok:
            logger.error(f"iam generate apply url fail: {message}")
            return settings.BK_IAM_SAAS_HOST
        return url

    def get_apply_data(self, actions: List[Union[ActionMeta, str]], resources: List[Resource] = None):
        """
        生成本系统无权限数据
        """
        resources = resources or []
        action_to_resources_list = []
        for action in actions:
            action = get_action_by_id(action)

            if not action.related_resource_types:
                # 如果没有关联资源，则直接置空
                resources = []

            action_to_resources_list.append({"action": action, "resources_list": [resources]})

        self.setup_meta()

        data = gen_perms_apply_data(
            system=settings.BK_IAM_SYSTEM_ID,
            subject=Subject("user", self.username),
            action_to_resources_list=action_to_resources_list,
        )

        url = self.get_apply_url(actions, resources)
        return data, url

    def is_allowed(
        self, action: Union[ActionMeta, str], resources: List[Resource] = None, raise_exception: bool = False
    ):
        """
        校验用户是否有动作的权限
        :param action: 动作
        :param resources: 依赖的资源实例列表
        :param raise_exception: 鉴权失败时是否需要抛出异常
        """
        action = get_action_by_id(action)
        if not action.related_resource_types:
            resources = []
        request = self.make_request(action, resources)

        try:
            result = self.iam_client.is_allowed(request)
        except AuthAPIError as e:
            logger.exception(f"[IAM AuthAPI Error]: {e}")
            result = False

        if not result and raise_exception:
            apply_data, apply_url = self.get_apply_data([action], resources)
            raise PermissionDeniedError(
                action_name=action.name,
                apply_url=apply_url,
                permission=apply_data,
            )

        return result

    def batch_is_allowed(self, actions: List[ActionMeta], resources: List[List[Resource]]):
        """
        查询某批资源某批操作是否有权限
        """
        request = self.make_multi_action_request(actions)
        result = self.iam_client.batch_resource_multi_actions_allowed(request, resources)
        return result

    @classmethod
    def make_resource(cls, resource_type: str, instance_id: str) -> Resource:
        """
        构造resource对象
        :param resource_type: 资源类型
        :param instance_id: 实例ID
        """
        resource_meta = get_resource_by_id(resource_type)
        return resource_meta.create_instance(instance_id)

    @classmethod
    def batch_make_resource(cls, resources: List[Dict]):
        """
        批量构造resource对象
        """
        return [cls.make_resource(r["type"], r["id"]) for r in resources]

    def get_system_info(self):
        """
        获取权限中心注册的动作列表
        """
        ok, message, data = self.iam_client._client.query(settings.BK_IAM_SYSTEM_ID)
        if not ok:
            raise GetSystemInfoError(_("获取系统信息错误：{message}").format(message=message))
        return data

    @classmethod
    def setup_meta(cls):
        """
        初始化权限中心实体
        """
        if getattr(cls, "__setup", False):
            return

        # 系统
        systems = [
            {"system_id": settings.BK_IAM_SYSTEM_ID, "system_name": settings.BK_IAM_SYSTEM_NAME},
            {"system_id": "bk_cmdb", "system_name": _("配置平台")},
        ]

        for system in systems:
            setup_system(**system)

        # 资源
        for r in _all_resources.values():
            setup_resource(r.system_id, r.id, r.name)

        # 动作
        for action in _all_actions.values():
            setup_action(system_id=settings.BK_IAM_SYSTEM_ID, action_id=action.id, action_name=action.name)

        cls.__setup = True
