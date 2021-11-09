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
from typing import Dict

import ujson as json
from django.template import engines

TEMPLATE = """import { request } from '../base';

{% for api in apis %}export const {{ api.name }} = request('{{ api.type }}', '{{ api.url | safe }}');
{% endfor %}
export default {
  {% for api in apis %}{% if forloop.last %}{{ api.name }},{% else %}{{ api.name }},
  {% endif %}{% endfor %}
};
"""

Timeout = 30
GW_group_excludes = ()
GW_api_includes = ()


def underscore_to_camel(underscore_format):
    """
    下划线命名 转 驼峰命名
    :param underscore_format: 下划线命名格式的字符串
    :return:
    """
    return "".join(word.capitalize() if i else word for i, word in enumerate(underscore_format.split("_")))


def remove_first_slash(url):
    """
    移除url中前面的 `/`
    """
    if url[0] == "/":
        return url[1:]
    return url


def route(api: Dict[str, str], double_brace: bool = False):
    url = (api["url"].format(), api["url"])[double_brace]
    if api["url"] in ("/get_gse_config/", "/report_log/", "/package/upload/", "/export/download/"):
        url = "/backend" + url
    elif api["group"] in ("subscription", "backend_plugin"):
        url = "/backend/api" + url
    elif api["group"] in ["rsa"]:
        url = "/core/api" + url
    else:
        url = "/api" + url
    return url


def main(is_apigw=False):
    apidoc_path = os.path.join("static", "apidoc")
    os.system(f"apidoc -i apps -o {apidoc_path}")
    with open(os.path.join(apidoc_path, "api_data.json"), "rb") as fh:
        apis = json.load(fh)

    grouped_data = {}
    if is_apigw:
        output = []
        for api in apis:
            if api["group"] in GW_group_excludes and api.get("name") not in GW_api_includes:
                continue
            url = route(api)
            data = {
                "path": url,
                "resource_name": api.get("name", "name"),
                "registed_http_method": api["type"],
                "description": api.get("title", ""),
                "dest_http_method": api["type"],
                "dest_url": f"http://{{stageVariables.domain}}{url}",
                "timeout": Timeout,
                "headers": {},
                "resource_classification": api["group"],
            }
            output.append(data)
        file_name = os.path.join("support-files", "api_gateway.json")
        with open(file_name, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(output))
        return file_name
    else:
        for api in apis:
            api["name"] = underscore_to_camel(api["name"])
            api["url"] = remove_first_slash(route(api, double_brace=True))
            group = api["group"].lower()
            grouped_data[group] = grouped_data.get(group, []) + [api]

        for group, data in grouped_data.items():
            file_name = os.path.join("frontend", "src", "api", "modules", "{}.js".format(group))
            template = engines["django"].from_string(TEMPLATE)
            code = template.render({"apis": data})
            with open(file_name, "w", encoding="utf-8") as fh:
                fh.write(code)


if __name__ == "__main__":
    main()
