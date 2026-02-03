# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask
from apps.backend.subscription.tools import fetch_biz_info_map
from apps.node_man.models import GlobalSettings


class Command(BaseCommand):
    help = """
    Migrate tools management command for Nodeman.
    
    Supported actions:
      - disable_periodic_task: Disable all periodic tasks
      - enable_periodic_task: Enable all periodic tasks
      - disable_subscription_task: Disable subscription tasks for all business units
      - enable_biz_subscription_task: Enable subscription task for a specific business unit (requires --bk_biz_id)
      - disable_biz_subscription_task: Disable subscription task for a specific business unit (requires --bk_biz_id)
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "-a", "--action",
            type=str,
            required=True,
            help="""Action to migrate tools. Supported actions:
                  disable_periodic_task, enable_periodic_task,
                  disable_subscription_task, enable_biz_subscription_task,
                  disable_biz_subscription_task"""
        )
        parser.add_argument(
            "-b", "--bk_biz_id",
            type=int,
            required=False,
            help="Business ID for enable_biz_subscription_task or disable_biz_subscription_task actions"
        )


    def disable_periodic_task(self, **kwargs):
        PeriodicTask.objects.update(enabled=False)
        print("Nodeman Migrate Tools: disable_periodic_task done")

    def enable_periodic_task(self, **kwargs):
        PeriodicTask.objects.update(enabled=True)
        print("Nodeman Migrate Tools: enable_periodic_task done")

    def disable_subscription_task(self, **kwargs):
        cc_all_biz = list(fetch_biz_info_map().values())
        cc_all_biz_ids = [biz["bk_biz_id"] for biz in cc_all_biz]
        GlobalSettings.objects.update_or_create(
            key=GlobalSettings.KeyEnum.DISABLE_SUBSCRIPTION_SCOPE_LIST.value,
            defaults={
                "v_json": cc_all_biz_ids,
            }
        )
        print("Nodeman Migrate Tools: disable_subscription_task done")

    def enable_biz_subscription_task(self, **kwargs):
        bk_biz_id = kwargs.get("bk_biz_id")
        if not bk_biz_id:
            print("Nodeman Migrate Tools: enable_biz_subscription_task missing bk_biz_id")
            return
        all_bizs = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.DISABLE_SUBSCRIPTION_SCOPE_LIST.value, default=[]
        )
        if int(bk_biz_id) in all_bizs:
            all_bizs.remove(int(bk_biz_id))
            GlobalSettings.update_config(
                key=GlobalSettings.KeyEnum.DISABLE_SUBSCRIPTION_SCOPE_LIST.value, value=all_bizs
            )
        print(f"Nodeman Migrate Tools: enable_biz_subscription_task done bk_biz_id: {bk_biz_id}")

    def disable_biz_subscription_task(self, **kwargs):
        bk_biz_id = kwargs.get("bk_biz_id")
        if not bk_biz_id:
            print("Nodeman Migrate Tools: disable_biz_subscription_task missing bk_biz_id")
            return
        all_bizs = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.DISABLE_SUBSCRIPTION_SCOPE_LIST.value, default=[]
        )
        all_bizs.append(int(bk_biz_id))
        GlobalSettings.update_config(
            key=GlobalSettings.KeyEnum.DISABLE_SUBSCRIPTION_SCOPE_LIST.value, value=all_bizs
        )
        print(f"Nodeman Migrate Tools: disable_biz_subscription_task done bk_biz_id: {bk_biz_id}")

    def handle(self, **kwargs):
        action = kwargs["action"]
        getattr(self, action)(**kwargs)
