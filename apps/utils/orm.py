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

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.utils.local import get_request_username


class SoftDeleteQuerySet(models.query.QuerySet):
    def delete(self, **kwargs):
        update_kv = {"is_deleted": True, "deleted_by": get_request_username(), "deleted_time": timezone.now()}
        update_count = self.update(**{**update_kv, **kwargs})
        return update_count


class SoftDeleteModelManager(models.Manager):
    """
    默认的查询和过滤方法, 不显示被标记为删除的记录
    """

    @classmethod
    def process_kwargs(cls, query_kwargs):
        if "is_deleted" in query_kwargs:
            return

        if not query_kwargs.pop("show_deleted", False):
            query_kwargs["is_deleted"] = False

    def all(self, *args, **kwargs):

        self.process_kwargs(kwargs)

        return super(SoftDeleteModelManager, self).filter(**kwargs)

    def filter(self, *args, **kwargs):

        self.process_kwargs(kwargs)

        return super(SoftDeleteModelManager, self).filter(*args, **kwargs)

    def get(self, *args, **kwargs):

        self.process_kwargs(kwargs)

        return super(SoftDeleteModelManager, self).get(*args, **kwargs)

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """
    需要记录删除操作的model父类
    自动记录删除时间与删除者
    对于此类的表提供软删除
    """

    objects = SoftDeleteModelManager()

    is_deleted = models.BooleanField(_("是否删除"), default=False)
    deleted_time = models.DateTimeField(_("删除时间"), blank=True, null=True)
    deleted_by = models.CharField(_("删除者"), max_length=32, blank=True, null=True)

    def delete(self, *args, **kwargs):
        """
        删除方法，不会删除数据
        而是通过标记删除字段 is_deleted 来软删除
        """
        self.is_deleted = True
        self.deleted_by = get_request_username()
        self.deleted_time = timezone.now()

        # 添加删除需要额外设置的值
        for extra_update_field, value in kwargs.items():
            if not hasattr(self, extra_update_field):
                continue
            setattr(self, extra_update_field, value)

        self.save()

    class Meta:
        abstract = True
