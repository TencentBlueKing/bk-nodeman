# -*- coding:utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from __future__ import unicode_literals

import time

from googletrans import Translator

"""
1. pip install googletrans  安装pip包
2. 在 TO_TRANSLATE_DICT 中放入待翻译的词条
3. python translate.py  执行翻译脚本

需要注意的是，如果一次性请求次数过多（亲测400个以下没问题）
ip地址可能会被谷歌加入黑名单，导致无法再请求调用
"""
TO_TRANSLATE_DICT = {
    "中文": "被翻译的语句",
    "提示": "提示语句",
}


def main():
    translator = Translator(service_urls=["translate.google.cn"])
    translated_dict = {}
    for key, value in TO_TRANSLATE_DICT.items():
        translated_dict[key] = translator.translate(value, dest="en").text
        print(f"'{key}': '{translated_dict[key]}',")
        # 睡1秒，避免限频
        time.sleep(1)
    print(translated_dict)


if __name__ == "__main__":
    main()
