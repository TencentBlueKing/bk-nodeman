# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.conf.urls import include, url
from iam.contrib.django.dispatcher import DjangoBasicResourceApiDispatcher
from rest_framework import routers

from apps.iam import Permission

dispatcher = DjangoBasicResourceApiDispatcher(Permission.get_iam_client(), settings.BK_IAM_SYSTEM_ID)

router = routers.DefaultRouter(trailing_slash=True)

urlpatterns = [url(r"^", include(router.urls)), url(r"^resource/$", dispatcher.as_view([login_exempt]))]
