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
from django.db import migrations


def update_isp_and_ap_region_city_id(apps, schema_editor):
    """更新全局配置中的ISP和存量接入点的region_id和city_id"""
    isp_list = [
        {"isp": "PrivateCloud", "isp_name": "企业私有云"},
        {"isp": "AWS", "isp_name": "亚马逊云"},
        {"isp": "Azure", "isp_name": "微软云"},
        {"isp": "GoogleCloud", "isp_name": "谷歌云"},
        {"isp": "SalesForce", "isp_name": "SalesForce"},
        {"isp": "OracleCloud", "isp_name": "Oracle Cloud"},
        {"isp": "IBMCloud", "isp_name": "IBM Cloud"},
        {"isp": "AlibabaCloud", "isp_name": "阿里云"},
        {"isp": "TencentCloud", "isp_name": "腾讯云"},
        {"isp": "ECloud", "isp_name": "中国电信"},
        {"isp": "UCloud", "isp_name": "UCloud"},
        {"isp": "MOS", "isp_name": "美团云"},
        {"isp": "KSyun", "isp_name": "金山云"},
        {"isp": "BaiduCloud", "isp_name": "百度云"},
        {"isp": "HuaweiCloud", "isp_name": "华为云"},
        {"isp": "capitalonline", "isp_name": "首都云"},
        {"isp": "TencentPrivateCloud", "isp_name": "腾讯自研云"},
        {"isp": "Zenlayer", "isp_name": "Zenlayer"},
    ]
    # 创建or更新ISP
    GlobalSettings = apps.get_model("node_man", "GlobalSettings")
    GlobalSettings.objects.update_or_create(defaults={"v_json": isp_list}, **{"key": "isp"})
    # 更新存量接入点的region_id和city_id
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    AccessPoint.objects.filter(region_id="test").update(region_id="default")
    AccessPoint.objects.filter(city_id="test").update(city_id="default")


class Migration(migrations.Migration):
    dependencies = [
        ("node_man", "0083_subscription_operate_info"),
    ]

    operations = [
        migrations.RunPython(update_isp_and_ap_region_city_id),
    ]
