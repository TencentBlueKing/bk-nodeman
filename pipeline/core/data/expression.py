# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2019 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import ast
import copy
import logging
import re

from mako import codegen, lexer
from mako.exceptions import MakoException

from pipeline import exceptions

logger = logging.getLogger("root")
# find mako template(format is ${xxx}，and ${}# not in xxx, # may raise memory error)
TEMPLATE_PATTERN = re.compile(r"\${[^${}#]+}")

# Whitelisted AST nodes for safe template expression evaluation.
# Any expression containing nodes outside this set will be rejected,
# preventing arbitrary code execution / SSTI via Mako templates.
_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Subscript,
    ast.Slice,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Call,
    ast.keyword,
    # Operators
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.FloorDiv,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
)

# Index node was removed in Python 3.9 but is still emitted on older versions.
if hasattr(ast, "Index"):
    _ALLOWED_AST_NODES = _ALLOWED_AST_NODES + (ast.Index,)

# Whitelisted callables that may be invoked from inside a template expression.
# Keep this list intentionally tiny, covering only formatting / type coercion
# and basic numeric helpers used by existing pipeline templates.
_SAFE_CALLABLES = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "len": len,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sum": sum,
    "sorted": sorted,
    "list": list,
    "tuple": tuple,
    "dict": dict,
    "set": set,
}

# Names that must never appear as identifiers in template expressions.
_FORBIDDEN_NAMES = {
    "exec",
    "eval",
    "compile",
    "open",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "__import__",
    "input",
    "breakpoint",
}


def _validate_ast(tree: ast.AST) -> None:
    """Walk the AST and reject any disallowed node, name or attribute access."""
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_AST_NODES):
            raise ValueError(f"Disallowed expression node: {type(node).__name__}")
        if isinstance(node, ast.Name):
            if node.id.startswith("_") or node.id in _FORBIDDEN_NAMES:
                raise ValueError(f"Disallowed name in template expression: {node.id}")
        if isinstance(node, ast.Call):
            # Only direct calls to whitelisted builtins are allowed.
            func = node.func
            if not isinstance(func, ast.Name) or func.id not in _SAFE_CALLABLES:
                raise ValueError("Only whitelisted callables are allowed in templates")


def _safe_eval_expression(expr: str, value_maps: dict):
    """
    Safely evaluate a template expression against ``value_maps``.

    Only a small whitelist of AST nodes and builtins is allowed, which keeps
    the engine compatible with existing pipeline templates such as
    ``${a + int(b)}`` or ``${a["c"]}`` while preventing Mako SSTI / RCE.
    """
    tree = ast.parse(expr.strip(), mode="eval")
    _validate_ast(tree)
    # No real builtins exposed; only the whitelisted callables and user vars.
    safe_globals = {"__builtins__": {}}
    safe_globals.update(_SAFE_CALLABLES)
    # value_maps wins over builtins so user-defined variables can shadow them
    # if needed.
    safe_locals = dict(value_maps)
    return eval(compile(tree, "<pipeline-template>", "eval"), safe_globals, safe_locals)  # noqa: S307


def format_constant_key(key):
    """
    @summary: format key to ${key}
    @param key:
    @return:
    """
    return "${%s}" % key


def deformat_constant_key(key):
    """
    @summary: deformat ${key} to key
    @param key:
    @return:
    """
    return key[2:-1]


class ConstantTemplate(object):
    def __init__(self, data):
        self.data = data

    def get_reference(self):
        reference = []
        templates = self.get_templates()
        for tpl in templates:
            reference += self.get_template_reference(tpl)
        reference = list(set(reference))
        return reference

    def get_templates(self):
        templates = []
        data = self.data
        if isinstance(data, str):
            templates += self.get_string_templates(data)
        if isinstance(data, (list, tuple)):
            for item in data:
                templates += ConstantTemplate(item).get_templates()
        if isinstance(data, dict):
            for value in list(data.values()):
                templates += ConstantTemplate(value).get_templates()
        return list(set(templates))

    def resolve_data(self, value_maps):
        data = self.data
        if isinstance(data, str):
            return self.resolve_string(data, value_maps)
        if isinstance(data, list):
            ldata = [""] * len(data)
            for index, item in enumerate(data):
                ldata[index] = ConstantTemplate(copy.deepcopy(item)).resolve_data(value_maps)
            return ldata
        if isinstance(data, tuple):
            ldata = [""] * len(data)
            for index, item in enumerate(data):
                ldata[index] = ConstantTemplate(copy.deepcopy(item)).resolve_data(value_maps)
            return tuple(ldata)
        if isinstance(data, dict):
            for key, value in list(data.items()):
                data[key] = ConstantTemplate(copy.deepcopy(value)).resolve_data(value_maps)
            return data
        return data

    @staticmethod
    def get_string_templates(string):
        return list(set(TEMPLATE_PATTERN.findall(string)))

    @staticmethod
    def get_template_reference(template):
        lex = lexer.Lexer(template)

        try:
            node = lex.parse()
        except MakoException as e:
            logger.warning("pipeline get template[{}] reference error[{}]".format(template, e))
            return []

        # Dummy compiler. _Identifiers class requires one
        # but only interested in the reserved_names field
        def compiler():
            return None

        compiler.reserved_names = set()
        identifiers = codegen._Identifiers(compiler, node)

        return list(identifiers.undeclared)

    @staticmethod
    def resolve_string(string, value_maps):
        if not isinstance(string, str):
            return string
        templates = ConstantTemplate.get_string_templates(string)

        # TODO keep render return object, here only process simple situation
        if len(templates) == 1 and templates[0] == string and deformat_constant_key(string) in value_maps:
            return value_maps[deformat_constant_key(string)]

        for tpl in templates:
            resolved = ConstantTemplate.resolve_template(tpl, value_maps)
            string = string.replace(tpl, resolved)
        return string

    @staticmethod
    def resolve_template(template, value_maps):
        if not isinstance(template, str):
            raise exceptions.ConstantTypeException("constant resolve error, template[%s] is not a string" % template)
        # Only ``${expr}`` style placeholders are accepted. This explicitly
        # disables Mako control blocks like ``<% ... %>`` and ``<%! ... %>``
        # which are powerful enough to import arbitrary modules.
        if not (template.startswith("${") and template.endswith("}")):
            logger.warning("pipeline reject non-expression template[%s]", template)
            return template
        expr = template[2:-1]
        try:
            resolved = _safe_eval_expression(expr, value_maps)
        except (NameError, KeyError) as e:
            logger.warning(
                "constant content is invalid, variable referred does not exist or variable type error[%s]" % e
            )
            return template
        except (ValueError, SyntaxError) as e:
            # ``ValueError`` is raised by the AST validator when the template
            # contains disallowed nodes (potential SSTI). ``SyntaxError`` is
            # raised by ``ast.parse`` for malformed expressions. In both cases
            # we keep the original placeholder unchanged, mirroring previous
            # behaviour for invalid input.
            logger.warning("pipeline rejected unsafe or invalid template[%s]: %s", template, e)
            return template
        except (TypeError, AttributeError) as e:
            logger.warning("constant content is invalid with error [%s]" % e)
            return template
        return str(resolved) if not isinstance(resolved, str) else resolved
