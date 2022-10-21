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
import typing
from dataclasses import dataclass, field

from . import base, models, targets


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


@dataclass
class VisibleRangeHandler:
    name: str
    version_str: str
    target_type: str
    visible_range_objs: typing.List[models.VisibleRange] = field(init=False)

    def __post_init__(self):
        self.visible_range_objs = models.VisibleRange.objects.filter(
            name=self.name, version=self.version_str, target_type=self.target_type
        )

    @classmethod
    def _is_visible(cls, visible_range_obj: models.VisibleRange, cmdb_obj: base.CmdbObj) -> bool:

        # 全部可见，直接返回 True
        if visible_range_obj.is_public:
            return True

        # 按可见范围规则找出对应的 CMDB 对象信息
        cmdb_obj_unit: typing.Optional[base.CmdbObjUnit] = cmdb_obj.obj_id__unit_map.get(visible_range_obj.bk_obj_id)
        # 没有提供相应的对象信息，视为不可见
        if cmdb_obj_unit is None:
            return False

        return cmdb_obj_unit.bk_inst_id in visible_range_obj.bk_inst_scope

    def is_visible(self, cmdb_obj: base.CmdbObj) -> bool:
        """
        资源是否对某个对象可见
        :param cmdb_obj: CMDB 对象信息
        :return:
        """
        for visible_range_obj in self.visible_range_objs:
            # 满足任一规则即可
            if self._is_visible(visible_range_obj, cmdb_obj):
                return True
        return False

    def is_belong_to_biz(self, bk_biz_id: int) -> bool:
        """
        资源是否属于给定业务
        :param bk_biz_id: 业务 ID
        :return:
        """
        for visible_range_obj in self.visible_range_objs:
            if visible_range_obj.bk_biz_id == bk_biz_id:
                return True
            if bk_biz_id in visible_range_obj.bk_inst_scope:
                return True
        return False
