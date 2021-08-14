# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import os

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.utils.crypto import get_random_string


class StorageFileOverwriteMixin:

    file_overwrite = settings.FILE_OVERWRITE

    def get_available_name(self, name, max_length=None):
        """重写获取文件有效名称函数，支持在 file_overwrite=True 时不随机生成文件名"""

        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)

        def _gen_random_name(_file_root) -> str:
            # 在文件名的起始位置添加随机串，源码规则为 "%s_%s%s" % (_file_root, get_random_string(7), file_ext)
            # 上述规则对 .tar.gz 不友好，会在类型后缀中间加随机串，所以改为随机串作为前缀
            return os.path.join(dir_name, "%s_%s%s" % (get_random_string(7), _file_root, file_ext))

        # not self.file_overwrite and self.exists(name) 利用 and 短路特点，如果 file_overwrite=True 就无需校验文件是否存在
        while (not self.file_overwrite and self.exists(name)) or (max_length and len(name) > max_length):
            # file_ext includes the dot.
            name = name if self.file_overwrite else _gen_random_name(file_root)

            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt to find an available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        "Please make sure that the corresponding file field "
                        'allows sufficient "max_length".' % name
                    )
                name = name if self.file_overwrite else _gen_random_name(file_root)
        return name
