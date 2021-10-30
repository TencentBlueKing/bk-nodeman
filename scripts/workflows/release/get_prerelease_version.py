# -*- coding: utf-8 -*-


import getopt
import os
import sys
from typing import Dict, Union

from packaging import version

HELP_TEXT = """
获取待发布的版本号
通用参数：
        [ -h, --help               [可选] "说明文档" ]
        [ -d, --dev-log-root       [必选] "开发日志目录路径" ]
"""


def extract_params(argv) -> Dict[str, Union[str, bool, int, float]]:
    try:
        opts, args = getopt.getopt(argv, "hd:", ["dev-log-root=", "help"])
    except getopt.GetoptError:
        print(HELP_TEXT)
        sys.exit(2)

    sh_params = {"dev-log-root": None}
    for opt, arg in opts:
        if opt in ("h", "--help"):
            print(HELP_TEXT)
            sys.exit(2)

        elif opt in ("-d", "--dev-log-root"):
            sh_params["dev-log-root"] = arg

    return sh_params


def get_prerelease_version(dev_log_root: str) -> str:
    version_ordered_list = sorted(os.listdir(dev_log_root), key=lambda v: version.parse(v))
    version_pending_release = version_ordered_list[-1]
    return version_pending_release


if __name__ == "__main__":
    params = extract_params(sys.argv[1:])
    try:
        print(get_prerelease_version(dev_log_root=params["dev-log-root"]))
    except FileNotFoundError as err:
        print(f"dev_log not found, err -> {err}")
        sys.exit(1)
