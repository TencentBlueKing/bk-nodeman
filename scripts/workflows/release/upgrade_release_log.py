# -*- coding: utf-8 -*-
import datetime
import getopt
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Union

import yaml
from get_prerelease_version import get_prerelease_version

HELP_TEXT = """
生成发布日志
通用参数：
        [ -h, --help                  [可选] "说明文档" ]
        [ -d, --dev-log-root          [必选] "开发日志目录路径" ]
        [ -r, --release-log-root      [必选] "发布日志路径" ]
        [ -p, --release-md-path       [可选] "发布日志readme文件路径，默认取 {release-log-root}/release.md" ]
        [ -v, --prerelease-version    [可选] "预发布版本，默认取dev-log-root最新的记录" ]
"""


def extract_params(argv) -> Dict[str, Union[str, bool, int, float]]:
    try:
        opts, args = getopt.getopt(
            argv, "hd:r:v:p:", ["dev-log-root=", "release-log-root=", "prerelease-version", "release-md-path", "help"]
        )
    except getopt.GetoptError:
        print(HELP_TEXT)
        sys.exit(2)

    sh_params = {"dev-log-root": None, "release-log-root": None, "prerelease-version": None, "release-md-path": None}
    for opt, arg in opts:
        if opt in ("h", "--help"):
            print(HELP_TEXT)
            sys.exit(2)

        elif opt in ("-d", "--dev-log-root"):
            sh_params["dev-log-root"] = arg

        elif opt in ("-r", "--release-log-root"):
            sh_params["release-log-root"] = arg

        elif opt in ("-v", "--prerelease-version"):
            sh_params["prerelease-version"] = arg

        elif opt in ("-p", "--release-md-path"):
            sh_params["release-md-path"] = arg
    return sh_params


if __name__ == "__main__":
    params = extract_params(sys.argv[1:])
    dev_log_root = params["dev-log-root"]
    release_log_root = params["release-log-root"]
    release_md_path = params["release-md-path"] or os.path.join(release_log_root, "release.md")

    # 获取等待发布的版本号
    prerelease_version = params["prerelease-version"] or get_prerelease_version(dev_log_root=dev_log_root)
    # 具体到某个版本的开发日志
    dev_yaml_dir_path = os.path.join(dev_log_root, prerelease_version)
    # 列举归档的yaml文件
    dev_yaml_file_name_list = os.listdir(dev_yaml_dir_path)
    # 根据pr类型对开发日志文本进行聚合
    msgs_group_by_pr_type: Dict[str, List[str]] = defaultdict(list)

    for dev_yaml_file_name in dev_yaml_file_name_list:
        dev_yaml_file_path = os.path.join(dev_yaml_dir_path, dev_yaml_file_name)

        try:
            with open(file=dev_yaml_file_path, encoding="utf-8") as dev_yaml_fs:
                dev_yaml = yaml.safe_load(dev_yaml_fs)
            for pr_type, user_msgs in dev_yaml.items():
                msgs_group_by_pr_type[pr_type].extend(user_msgs)
        except Exception:
            # 忽略解析错误的开发日志
            continue

    # 拼接日志
    release_text = f"\n## {prerelease_version} - {datetime.date.today()} \n"
    for pr_type, msgs in msgs_group_by_pr_type.items():
        release_text += f"\n\n### {pr_type}: \n  * " + "\n  * ".join(msgs)

    # 如果发布日志目录路径不存在，逐层进行创建，并且忽略已创建的层级（exist_ok）
    if not os.path.exists(release_log_root):
        os.makedirs(release_log_root, exist_ok=True)

    release_md_title = "# Release\n"
    if not os.path.exists(release_md_path):
        os.makedirs(os.path.basename(release_md_path), exist_ok=True)
        with open(file=release_md_path, mode="w+", encoding="utf-8") as release_md_fs:
            release_md_fs.write(release_md_title)

    # 标志位，记录是否已经写入
    is_release_text_write = False
    with open(file=release_md_path, mode="r", encoding="utf-8") as release_md_fs:
        # 整体数据量不大，全部读取
        all_release_text = release_md_fs.read()
        # 判断日志是否已经写入
        if release_text in all_release_text:
            is_release_text_write = True

    if not is_release_text_write:
        with open(file=release_md_path, mode="w", encoding="utf-8") as release_md_fs:
            new_all_release_text = (
                release_md_title + release_text + "\n" + all_release_text.replace(release_md_title, "")
            )
            release_md_fs.write(new_all_release_text)

    # 删除该版本的多余发布日志
    for release_md_path_to_be_deleted in Path(release_log_root).glob(f"V{prerelease_version}*.md"):
        os.remove(release_md_path_to_be_deleted)

    # 另写一份发布日志到 version-date.md
    version_release_md_path = os.path.join(
        release_log_root, f"V{prerelease_version}_{datetime.datetime.now().strftime('%Y%m%d')}.md"
    )
    # w -> overwrite
    with open(file=version_release_md_path, mode="w", encoding="utf-8") as version_release_md_fs:
        version_release_md_fs.write(release_text + "\n")

    print(version_release_md_path)
