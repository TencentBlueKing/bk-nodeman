# -*- coding: utf-8 -*-
import datetime
import getopt
import os
import sys
from pathlib import Path
from typing import Dict, Union

HELP_TEXT = """
生成发布日志
通用参数：
        [ -h, --help                  [可选] "说明文档" ]
        [ -r, --release-log-root      [必选] "发布日志路径" ]
        [ -p, --release-md-path       [可选] "发布日志readme文件路径，默认取 {release-log-root}/readme.md" ]
        [ -v, --prerelease-version    [必选] "预发布版本" ]
        [ -l, --changelog-path        [必选] "变更日志路径" ]
"""


def extract_params(argv) -> Dict[str, Union[str, bool, int, float]]:
    try:
        opts, args = getopt.getopt(
            argv,
            "hr:v:p:l:",
            ["release-log-root=", "prerelease-version=", "release-md-path=", "changelog-path=", "help"],
        )
    except getopt.GetoptError:
        print(HELP_TEXT)
        sys.exit(2)

    sh_params = {"release-log-root": None, "prerelease-version": None, "release-md-path": None, "changelog-path": None}
    for opt, arg in opts:
        if opt in ("h", "--help"):
            print(HELP_TEXT)
            sys.exit(2)

        elif opt in ("-r", "--release-log-root"):
            sh_params["release-log-root"] = arg

        elif opt in ("-v", "--prerelease-version"):
            sh_params["prerelease-version"] = arg

        elif opt in ("-p", "--release-md-path"):
            sh_params["release-md-path"] = arg

        elif opt in ("-l", "--changelog-path"):
            sh_params["changelog-path"] = arg
    return sh_params


if __name__ == "__main__":
    params = extract_params(sys.argv[1:])
    changelog_path = params["changelog-path"]
    release_log_root = params["release-log-root"]
    prerelease_version = params["prerelease-version"]
    release_md_path = params["release-md-path"] or os.path.join(release_log_root, "readme.md")

    with open(file=changelog_path, mode="r", encoding="utf-8") as changelog_fs:
        # 整体数据量不大，全部读取
        changelog = changelog_fs.read()

    # 拼接日志
    release_text = f"\n## {prerelease_version} - {datetime.date.today()} \n\n{changelog}"

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
