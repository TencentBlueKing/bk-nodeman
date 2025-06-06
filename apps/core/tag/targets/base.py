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
import abc
import logging
import typing

import wrapt
from django.db import transaction
from django.db.models import Model

from apps.core.tag.models import Tag
from apps.utils import cache

from .. import constants, exceptions, models

logger = logging.getLogger("app")


class TagChangeRecorder:
    def __init__(self, is_delete: bool = False):
        self.is_delete = is_delete

    @classmethod
    def handle_create_or_update(cls, instance: typing.Type["BaseTargetHelper"]):
        """
        处理
        :param instance:
        :return:
        """
        # 发布标签版本后，创建或更新相应的标签
        tag, created = models.Tag.objects.update_or_create(
            target_version=instance.target_version,
            target_id=instance.target_id,
            target_type=instance.TARGET_TYPE,
            name=instance.tag_name,
        )
        logger.info(
            f"[publish_tag_version] update_or_create tag -> {tag.name}({tag.id}) success, "
            f"target_helper -> {instance}"
        )

        if created:
            action = constants.TagChangeAction.CREATE.value
        else:
            # 找到最后一次变更记录
            last_record: models.TagChangeRecord = (
                models.TagChangeRecord.objects.filter(tag_id=tag.id).order_by("-id").first()
            )
            action = constants.TagChangeAction.UPDATE.value
            # 最后一次变更记录同当前变更版本一致，视为覆盖动作
            if last_record and last_record.target_version == instance.target_version:
                action = constants.TagChangeAction.OVERWRITE.value

        # 保存变更记录
        models.TagChangeRecord.objects.create(tag_id=tag.id, action=action, target_version=instance.target_version)
        logger.info(
            f"[publish_tag_version] recorded change: tag -> {tag.name}({tag.id}), action -> {action}, "
            f"target_version -> {instance.target_version}"
        )
        return tag

    @classmethod
    def handle_delete(cls, instance: typing.Type["BaseTargetHelper"]):
        tag: models.Tag = models.Tag.objects.get(
            name=instance.tag_name,
            target_id=instance.target_id,
            target_type=instance.TARGET_TYPE,
        )
        # 删除标签前，创建变更记录
        models.TagChangeRecord.objects.create(
            tag_id=tag.id, action=constants.TagChangeAction.DELETE.value, target_version=instance.target_version
        )
        logger.info(
            f"[delete_tag_version] recorded delete change: tag -> {tag.name}({tag.id}), "
            f"target_version -> {instance.target_version}"
        )

        # 删除标签
        tag.delete()
        logger.info(
            f"[delete_tag_version] deleted tag -> {tag.name}({tag.id}) success, " f"target_helper -> {instance}"
        )

        return tag

    @wrapt.decorator
    def __call__(
        self,
        wrapped: typing.Callable,
        instance: typing.Type["BaseTargetHelper"],
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        """
        :param wrapped: 被装饰的函数或类方法
        :param instance:
            - 如果被装饰者为普通类方法，该值为类实例
            - 如果被装饰者为 classmethod / 类方法，该值为类
            - 如果被装饰者为类/函数/静态方法，该值为 None
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """

        with transaction.atomic():

            wrapped(*args, **kwargs)

            if not self.is_delete:
                return self.handle_create_or_update(instance)
            else:
                return self.handle_delete(instance)


class BaseTargetHelper(abc.ABC):

    # 目标对象存储使用的唯一键
    PK: str = "id"
    # 目标类型
    TARGET_TYPE: str = None
    # 目标对象模型
    MODEL: typing.Type[Model] = None

    # 标签名称
    tag_name: str = None
    # 目标 ID
    target_id: int = None
    # 标签对应的目标版本
    target_version: str = None

    @classmethod
    def get_target(cls, target_id: int):
        """
        获取目标对象
        :param target_id: 目标 ID
        :return:
        """
        try:
            return cls.MODEL.objects.get(**{cls.PK: target_id})
        except cls.MODEL.DoesNotExist:
            raise exceptions.TargetNotExistError({"target_id": target_id})

    @classmethod
    def get_tag(cls, target_id: int, target_version: str) -> models.Tag:
        """
        获取标签
        :param target_id: 目标 ID
        :param target_version: 目标版本
        :return:
        """
        try:
            return models.Tag.objects.get(
                target_id=target_id, target_type=cls.TARGET_TYPE, target_version=target_version
            )
        except models.Tag.DoesNotExist:
            raise exceptions.TagNotExistError({"target_id": target_id, "target_type": cls.TARGET_TYPE})

    @classmethod
    def get_tag_name__obj_map(cls, target_id: int) -> typing.Dict[str, models.Tag]:
        """
        获取指定目标 ID 的 标签名称及对象映射关系
        :param target_id: 目标 ID
        :return:
        """
        tag_name__obj_map: typing.Dict[str, models.Tag] = {}
        for tag in models.Tag.objects.filter(target_id=target_id, target_type=cls.TARGET_TYPE):
            tag_name__obj_map[tag.name] = tag
        return tag_name__obj_map

    @classmethod
    def get_top_tag_or_none(cls, target_id: int) -> typing.Optional[models.Tag]:
        """
        获取指定目标 ID 的置顶标签，不存在则返回 None
        :param target_id: 目标 ID
        :return:
        """
        return models.Tag.objects.filter(target_id=target_id, to_top=True).first()

    @classmethod
    def get_target_version(cls, target_id: int, target_version: str) -> str:
        tag_name__obj_map: typing.Dict[str, Tag] = cls.get_tag_name__obj_map(
            target_id=target_id,
        )
        # 如果版本号匹配到标签名称，取对应标签下的真实版本号
        if target_version in tag_name__obj_map:
            target_version: str = tag_name__obj_map[target_version].target_version

        return target_version

    def __str__(self):
        return f"[{self.__class__.__name__}({self.tag_name}|{self.target_id}|{self.target_version})]"

    def __init__(self, tag_name: str, target_id: int, target_version: str):
        self.tag_name = tag_name
        self.target_id = target_id
        self.target_version = target_version

    @property
    @cache.class_member_cache()
    def target(self):
        """获取目标对象"""
        return self.get_target(self.target_id)

    @TagChangeRecorder()
    def publish_tag_version(self):
        """
        将标签视为版本，发布到对应目标
        :return:
        """
        logger.info(f"[publish_tag_version] publish tag version to target start, target_helper -> {self}")
        self._publish_tag_version()
        logger.info(f"[publish_tag_version] publish tag version to target finished, target_helper -> {self}")

    @TagChangeRecorder(is_delete=True)
    def delete_tag_version(self):
        self._delete_tag_version()

    @abc.abstractmethod
    def _publish_tag_version(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _delete_tag_version(self):
        raise NotImplementedError
