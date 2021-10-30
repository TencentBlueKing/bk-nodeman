# -*- coding: utf-8 -*-

import getopt
import re
import sys
from typing import Dict, Union

HELP_TEXT = """
版本号递增
通用参数：
        [ -h, --help             [可选] "说明文档" ]
        [ -v, --version          [必选] "开发日志目录路径" ]
"""


def extract_params(argv) -> Dict[str, Union[str, bool, int, float]]:
    try:
        opts, args = getopt.getopt(argv, "hv:", ["version=", "help"])
    except getopt.GetoptError:
        print(HELP_TEXT)
        sys.exit(2)

    sh_params = {"version": None}
    for opt, arg in opts:
        if opt in ("h", "--help"):
            print(HELP_TEXT)
            sys.exit(2)

        elif opt in ("-v", "--version"):
            sh_params["version"] = arg

    return sh_params


VERSION_SEP = "."
VERSION_PATTERN_OBJ = re.compile(r"\d+\.\d+\.\d+")


def version_increment(version_number: str) -> str:
    if not VERSION_PATTERN_OBJ.match(version_number):
        raise TypeError(f"version -> {version_number} invalid.")

    major, minor, patch = version_number.split(VERSION_SEP)

    return VERSION_SEP.join([major, minor, str(int(patch) + 1)])


if __name__ == "__main__":
    params = extract_params(sys.argv[1:])
    try:
        print(version_increment(version_number=params["version"]))
    except TypeError as err:
        print(f"err -> {err}")
        sys.exit(1)
