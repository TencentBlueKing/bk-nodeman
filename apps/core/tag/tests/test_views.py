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

from apps.backend.tests.plugin import utils
from apps.node_man import models as node_man_models

from .. import constants, models


class TagPluginTestCase(utils.PluginBaseTestCase):
    DEFAULT_TAG_NAME: str = "stable2"

    def create_tag(self, tag_name: str, target_version: str) -> typing.Dict[str, typing.Any]:
        upload_result = self.upload_plugin()
        self.register_plugin(upload_result["name"])

        plugin_obj: node_man_models.GsePluginDesc = node_man_models.GsePluginDesc.objects.get(name=utils.PLUGIN_NAME)

        create_result: typing.Dict[str, typing.Any] = self.client.post(
            path="/core/api/tag/",
            data={
                "name": tag_name,
                "target_type": constants.TargetType.PLUGIN.value,
                "target_id": plugin_obj.id,
                "target_version": target_version,
            },
        )
        return create_result

    def test_create(self):
        tag_info: typing.Dict[str, typing.Any] = self.create_tag(
            tag_name=self.DEFAULT_TAG_NAME, target_version=utils.PACKAGE_VERSION
        )["data"]
        tag_change_record_obj: models.TagChangeRecord = models.TagChangeRecord.objects.get(tag_id=tag_info["id"])
        self.assertEqual(tag_change_record_obj.target_version, tag_info["target_version"])
        self.assertEqual(tag_change_record_obj.action, constants.TagChangeAction.CREATE.value)

        tag_version_pkg_ids: typing.List[int] = list(
            node_man_models.Packages.objects.filter(project=utils.PLUGIN_NAME, version=tag_info["name"]).values_list(
                "id", flat=True
            )
        )
        target_version_pkg_ids: typing.List[int] = list(
            node_man_models.Packages.objects.filter(
                project=utils.PLUGIN_NAME, version=utils.PACKAGE_VERSION
            ).values_list("id", flat=True)
        )
        self.assertEqual(len(target_version_pkg_ids), len(tag_version_pkg_ids))
        self.assertEqual(
            node_man_models.PluginConfigTemplate.objects.filter(
                plugin_name=utils.PLUGIN_NAME, plugin_version=utils.PACKAGE_VERSION
            ).count(),
            node_man_models.PluginConfigTemplate.objects.filter(
                plugin_name=utils.PLUGIN_NAME, plugin_version=tag_info["name"]
            ).count(),
        )
        self.assertEqual(
            node_man_models.ProcControl.objects.filter(plugin_package_id__in=tag_version_pkg_ids).count(),
            node_man_models.ProcControl.objects.filter(plugin_package_id__in=target_version_pkg_ids).count(),
        )

    def test_partial_update__version(self):
        tag_info: typing.Dict[str, typing.Any] = self.create_tag(
            tag_name=self.DEFAULT_TAG_NAME, target_version=utils.PACKAGE_VERSION
        )["data"]
        self.client.patch(path=f"/core/api/tag/{tag_info['id']}/", data={"target_version": tag_info["target_version"]})
        self.assertTrue(
            models.TagChangeRecord.objects.filter(
                tag_id=tag_info["id"],
                target_version=tag_info["target_version"],
                action=constants.TagChangeAction.OVERWRITE.value,
            ).exists()
        )

    def test_partial_update__other_fields(self):
        tag_info: typing.Dict[str, typing.Any] = self.create_tag(
            tag_name=self.DEFAULT_TAG_NAME, target_version=utils.PACKAGE_VERSION
        )["data"]

        update_params: typing.Dict[str, typing.Any] = {"description": "description", "to_top": True}
        self.client.patch(path=f"/core/api/tag/{tag_info['id']}/", data=update_params)
        models.Tag.objects.get(id=tag_info["id"], **update_params)
        self.assertEqual(models.TagChangeRecord.objects.filter(tag_id=tag_info["id"]).count(), 1)

    def test_delete(self):
        tag_info: typing.Dict[str, typing.Any] = self.create_tag(
            tag_name=self.DEFAULT_TAG_NAME, target_version=utils.PACKAGE_VERSION
        )["data"]

        before_delete_tag_version_pkg_ids = list(
            node_man_models.Packages.objects.filter(project=utils.PLUGIN_NAME, version=tag_info["name"]).values_list(
                "id", flat=True
            )
        )

        self.client.delete(path=f"/core/api/tag/{tag_info['id']}/")

        tag_version_pkg_ids: typing.List[int] = list(
            node_man_models.Packages.objects.filter(project=utils.PLUGIN_NAME, version=tag_info["name"]).values_list(
                "id", flat=True
            )
        )

        self.assertEqual(len(tag_version_pkg_ids), 0)
        self.assertEqual(
            node_man_models.PluginConfigTemplate.objects.filter(
                plugin_name=utils.PLUGIN_NAME, plugin_version=tag_info["name"]
            ).count(),
            0,
        )
        self.assertEqual(
            node_man_models.ProcControl.objects.filter(plugin_package_id__in=before_delete_tag_version_pkg_ids).count(),
            0,
        )
        self.assertTrue(
            models.TagChangeRecord.objects.filter(
                tag_id=tag_info["id"],
            ).count()
        )
        self.assertFalse(models.Tag.objects.filter(id=tag_info["id"]).exists())
