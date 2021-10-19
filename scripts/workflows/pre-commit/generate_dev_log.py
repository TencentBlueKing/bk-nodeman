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
import subprocess
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List

import ruamel.yaml
from packaging import version
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

DEV_LOG_ROOT = "dev_log"
WF_CMD_PATTERN = "(wf -l)"


def parse_commit_message(commit_message: str) -> Dict[str, str]:
    """
    解析提交信息
    :param commit_message: git提交信息
    :return: 写入yaml的结构
    """
    commit_type, commit_content = commit_message.split(":", maxsplit=1)
    return {"commit_type": commit_type.strip(), "commit_content": commit_content.strip()}


def get_commit_message() -> Dict[str, str]:
    print("flag", sys.argv)
    if len(sys.argv) <= 1:
        raise ValueError("Can't not find commit message path.")
    commit_message_file_path = sys.argv[1]
    with open(commit_message_file_path, "r", encoding="utf-8") as fs:
        commit_message = fs.read()

    return {"commit_message": commit_message, "commit_message_file_path": commit_message_file_path}


def get_git_username() -> str:
    """
    获取git username
    :return: git username
    """
    # 优先取本地配置
    resource_cmd_list = [["git", "config", "user.name"], ["git", "config", "--global", "user.name"]]

    for resource_cmd in resource_cmd_list:
        process = subprocess.Popen(resource_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, __ = process.communicate()
        out = out.decode(encoding="utf-8")
        if out.endswith("\n"):
            out = out[:-1]
        if out:
            return out

    raise ValueError("get git username error: confirm your config.")


def check_is_record(dev_log_yaml_paths: List[str], commit_msg_parse_result: Dict[str, str]) -> bool:
    """
    检查是否已记录提交日志
    :param dev_log_yaml_paths: 需要检查的文件
    :param commit_msg_parse_result: 提交信息解析结果
    :return: bool 是否已记录
    """
    for dev_log_yaml_path in dev_log_yaml_paths:
        if not os.path.exists(dev_log_yaml_path):
            continue
        with open(file=dev_log_yaml_path, mode="r", encoding="utf-8") as fs:
            content = fs.read()
            if commit_msg_parse_result["commit_content"] in content:
                return True
    return False


def generate_dev_log(dev_log_root: str, commit_message: str) -> Dict[str, Any]:
    """
    根据 git 提交信息生成 dev_log
    :param dev_log_root: dev_log 目录
    :param commit_message: git 提交信息
    :return:
    """
    version_list = os.listdir(dev_log_root)
    if not version_list:
        raise ValueError(f"dev_log_path -> {dev_log_root} version dev log dir not exist.")
    rc_version = sorted(version_list, key=lambda v: version.parse(v))[-1]
    git_username = get_git_username()
    dt_str = datetime.now().strftime("%Y%m%d%H%M")
    user_dev_log_yaml_path = os.path.join(dev_log_root, rc_version, f"{git_username}_{dt_str}.yaml")
    commit_msg_parse_result = parse_commit_message(commit_message)

    check_is_record_yaml_paths = []
    for yaml_file_name in os.listdir(os.path.join(dev_log_root, rc_version)):
        check_is_record_yaml_paths.append(os.path.join(dev_log_root, rc_version, yaml_file_name))
    is_record = check_is_record(
        dev_log_yaml_paths=check_is_record_yaml_paths, commit_msg_parse_result=commit_msg_parse_result
    )
    if is_record:
        return {"is_generated": False}

    # 不存在时新建 yaml
    if not os.path.exists(user_dev_log_yaml_path):
        with open(file=user_dev_log_yaml_path, mode="w+"):
            pass

    else:
        with open(file=user_dev_log_yaml_path, mode="a", encoding="utf-8") as fs:
            fs.write("\n")

    with open(file=user_dev_log_yaml_path, encoding="utf-8") as yaml_fs:
        yaml_info = ruamel.yaml.round_trip_load(yaml_fs, preserve_quotes=True)

    # 空yaml文件 yaml_info 为 None
    yaml_info = yaml_info or {}
    commit_type = commit_msg_parse_result["commit_type"]
    commit_content = commit_msg_parse_result["commit_content"]

    # DoubleQuotedScalarString -> 保存时携带双引号
    # 参考：https://stackoverflow.com/questions/39262556/preserve-quotes-and-also-add-data-with-quotes-in-ruamel
    yaml_info[commit_type] = yaml_info.get("commit_type", []) + [DoubleQuotedScalarString(commit_content)]

    with open(file=user_dev_log_yaml_path, mode="w", encoding="utf-8") as yaml_fs:
        ruamel.yaml.round_trip_dump(yaml_info, yaml_fs, explicit_start=True, block_seq_indent=2)

    subprocess.call(["git", "add", user_dev_log_yaml_path])

    return {"is_generated": True, "user_dev_log_yaml_path": user_dev_log_yaml_path}


def main() -> int:
    get_commit_message_result = get_commit_message()
    commit_message_untreated = get_commit_message_result["commit_message"]
    commit_message_file_path = get_commit_message_result["commit_message_file_path"]
    if WF_CMD_PATTERN not in commit_message_untreated:
        print("workflow command not found, skip")
        return 0

    commit_message = commit_message_untreated.replace(WF_CMD_PATTERN, "")
    if commit_message.endswith("\n"):
        commit_message = commit_message[:-1]

    try:
        generate_dev_log_result = generate_dev_log(dev_log_root=DEV_LOG_ROOT, commit_message=commit_message)

        with open(file=commit_message_file_path, mode="w", encoding="utf-8") as fs:
            fs.write(commit_message)

        if generate_dev_log_result["is_generated"]:
            print(f"generated dev log yaml -> {generate_dev_log_result['user_dev_log_yaml_path']}")
            return 1

    except Exception as e:
        print(f"Failed to generate dev log: {e}, traceback -> {traceback.format_exc()}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
