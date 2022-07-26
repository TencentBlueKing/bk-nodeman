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

from rest_framework import serializers

from apps.node_man import constants


class NodeSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(required=False)
    bk_inst_id = serializers.IntegerField(required=False)
    bk_obj_id = serializers.CharField(required=False)
    bk_host_id = serializers.IntegerField(required=False)
    ip = serializers.CharField(required=False)
    bk_cloud_id = serializers.IntegerField(required=False)
    bk_supplier_id = serializers.IntegerField(default=constants.DEFAULT_SUPPLIER_ID)
    instance_info = serializers.DictField(required=False)
