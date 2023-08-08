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

from apps.core.tag.models import Tag

from .. import constants
from . import base

logger = logging.getLogger("app")


class AgentTargetHelper(base.BaseTargetHelper):

    MODEL = None
    TARGET_TYPE = constants.TargetType.AGENT.value

    def _publish_tag_version(self):
        Tag.objects.update_or_create(
            defaults={"target_version": self.target_version},
            name=self.tag_name,
            target_id=self.target_id,
            target_type=self.TARGET_TYPE,
        )

    def _delete_tag_version(self):
        return super()._delete_tag_version()
