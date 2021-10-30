# -*- coding: utf-8 -*-
import getopt
import re
import sys
from enum import Enum
from typing import Dict, List, Optional, Union

import ruamel.yaml

HELP_TEXT = """
提取yaml文件指定关键路径信息
通用参数：
        [ -h, --help                 [可选] "说明文档" ]
        [ -f, --yaml-path            [必选] "yaml文件路径" ]
        [ -k, --keyword-path         [必选] "关键路径，例如：a->b" ]
        [ -o, --op                   [必选] "操作，set, get" ]
        [ -v, --value                [可选] "值，op=set必选" ]
"""


def extract_params(argv) -> Dict[str, Union[str, bool, int, float]]:
    try:
        opts, args = getopt.getopt(argv, "hf:k:o:v:", ["yaml-path=", "keyword-path=", "op=", "value=", "help"])
    except getopt.GetoptError:
        print(HELP_TEXT)
        sys.exit(2)

    sh_params = {"yaml-path": None, "keyword-path": None, "op": None, "value": None}
    for opt, arg in opts:
        if opt in ("h", "--help"):
            print(HELP_TEXT)
            sys.exit(2)

        elif opt in ("-f", "--yaml-path"):
            sh_params["yaml-path"] = arg

        elif opt in ("-k", "--keyword-path"):
            sh_params["keyword-path"] = arg

        elif opt in ("-o", "--op"):
            sh_params["op"] = arg

        elif opt in ("-v", "--value"):
            sh_params["value"] = arg

    return sh_params


# 路径分隔符
KEY_PATH_SEP = "->"
# 索引分隔符
IDX_SEP = ":"
# 索引匹配正则
IDX_PATTERN_OBJ = re.compile(r"index:([\-\+]?\d+)")


class YamlOpType(Enum):
    SET = "set"
    GET = "get"

    @classmethod
    def get_choices(cls):
        return [cls.GET.value, cls.SET.value]


def parse_keyword_path(keyword_path: str) -> List[str]:
    """
    解析关键路径
    :param keyword_path: 关键路径
    :return: 分割后的寻址片段
    """
    return keyword_path.strip().split(sep=KEY_PATH_SEP)


def find_and_op_yaml_info(
    yaml_info: Union[Dict, List],
    kw_path_steps: List[str],
    op: str,
    value: Optional[Union[Dict, List, str, int, float]] = None,
):
    """
    查找并操作相应的yaml键
    :param yaml_info: yaml数据结构
    :param kw_path_steps: 寻址片段
    :param op: 操作
    :param value: 值，在 op=set 时，会作为新的键值
    :return: 查找到的键值
    """

    # 当前遍历节点
    current_root = yaml_info

    for index, kw_path_step in enumerate(kw_path_steps):
        # 匹配到列表索引
        if IDX_PATTERN_OBJ.match(kw_path_step):
            __, idx_key = kw_path_step.strip().split(IDX_SEP)
            idx_key = int(idx_key)
            if not isinstance(current_root, list):
                raise TypeError(f"step -> {kw_path_step} except list but get type -> {type(current_root)}.")
            elif len(current_root) <= abs(idx_key):
                raise IndexError(f"step index -> {idx_key}, but len -> {len(current_root)}.")

            next_root = current_root[idx_key]
        else:
            if kw_path_step not in current_root:
                raise KeyError(f"step -> {kw_path_step} not found.")
            idx_key = kw_path_step
            next_root = current_root[idx_key]

        # 遍历结束
        if index == len(kw_path_steps) - 1:
            if op == YamlOpType.SET.value:
                current_root[idx_key] = value
            return next_root

        current_root = next_root


def op_yaml(
    yaml_path: str,
    keyword_path: str,
    op: str,
    value: Optional[Union[Dict, List, str, int, float]] = None,
) -> Optional[Union[Dict, List, str, int, float]]:
    """
    操作 yaml
    :param yaml_path: yaml文件路径
    :param keyword_path: 关键路径
    :param op: 操作
    :param value: 值，在 op=set 时，会作为新的键值
    :return: 查找到的键值
    """
    # PyYAML 默认不保存注释，所以使用 ruamel.yaml 作为解析模块
    # 参考：https://stackoverflow.com/questions/7255885/save-dump-a-yaml-file-with-comments-in-pyyaml
    yaml = ruamel.yaml.YAML()
    # 保存时不去掉引号，参考：https://stackoverflow.com/questions/42094599/preserving-quotes-in-ruamel-yaml
    yaml.preserve_quotes = True
    with open(file=yaml_path, encoding="utf-8") as yaml_fs:
        yaml_info = yaml.load(yaml_fs)

    kw_result = find_and_op_yaml_info(
        yaml_info=yaml_info,
        kw_path_steps=parse_keyword_path(keyword_path=keyword_path),
        op=op,
        value=value,
    )

    if op != YamlOpType.SET.value:
        return kw_result

    with open(yaml_path, "w") as yaml_fs:
        yaml.dump(yaml_info, yaml_fs)

    return kw_result


if __name__ == "__main__":
    params = extract_params(sys.argv[1:])

    result = op_yaml(
        yaml_path=params["yaml-path"],
        keyword_path=params["keyword-path"],
        op=params["op"],
        value=params["value"],
    )

    print(result)
