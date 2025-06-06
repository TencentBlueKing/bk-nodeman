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


import logging
import typing

from apps.core.tag.models import Tag
from apps.node_man.models import GsePackageDesc

from .. import constants
from . import base

logger = logging.getLogger("app")


class AgentTargetHelper(base.BaseTargetHelper):

    MODEL = None
    TARGET_TYPE = constants.TargetType.AGENT.value

    def _publish_tag_version(self):
        if self.tag_name in ["stable", "latest", "test"]:
            # 内置标签相互覆盖
            Tag.objects.update_or_create(
                defaults={"target_version": self.target_version},
                name=self.tag_name,
                target_id=self.target_id,
                target_type=self.TARGET_TYPE,
            )
            return

        tag: typing.Optional[Tag] = Tag.objects.filter(
            name=self.tag_name,
            target_id=self.target_id,
            target_type=self.TARGET_TYPE,
        ).first()

        if not tag:
            return

        if not tag.target_version:
            # 刚创建的未指定版本的标签
            tag.target_version = self.target_version
            tag.save()
        else:
            Tag.objects.update_or_create(
                name=self.tag_name,
                target_id=self.target_id,
                target_type=self.TARGET_TYPE,
                target_version=self.target_version,
                description=tag.description,
            )

    def _delete_tag_version(self):
        pass

    @classmethod
    def get_agent_name_target_id_map(cls) -> typing.Dict[str, int]:
        package_descs = GsePackageDesc.objects.values("project", "id")
        return {package_desc["project"]: package_desc["id"] for package_desc in package_descs}
