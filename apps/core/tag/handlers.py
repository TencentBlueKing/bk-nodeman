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
from . import models, targets


class TagHandler:
    @classmethod
    def publish_tag_version(
        cls,
        name: str,
        target_type: str,
        target_id: int,
        target_version: str,
    ) -> models.Tag:
        """
        将标签视为版本，发布到对应目标
        :param name: 标签名称
        :param target_type: 目标类型
        :param target_id: 目标 ID
        :param target_version: 目标版本
        :return:
        """
        target_helper: targets.BaseTargetHelper = targets.get_target_helper(target_type)(
            tag_name=name, target_id=target_id, target_version=target_version
        )
        return target_helper.publish_tag_version()

    @classmethod
    def delete_tag_version(
        cls,
        name: str,
        target_type: str,
        target_id: int,
        target_version: str,
    ) -> models.Tag:
        """
        将标签视为版本，发布到对应目标
        :param name: 标签名称
        :param target_type: 目标类型
        :param target_id: 目标 ID
        :param target_version: 目标版本
        :return:
        """
        target_helper: targets.BaseTargetHelper = targets.get_target_helper(target_type)(
            tag_name=name, target_id=target_id, target_version=target_version
        )
        return target_helper.delete_tag_version()


class TagChangeRecordHandler:
    pass
