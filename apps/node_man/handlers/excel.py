# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
import re
from typing import Any, Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile
from openpyxl import Workbook, load_workbook

from apps.node_man import constants, models
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.tools.excel import ExcelTools
from apps.node_man.tools.host import HostTools

logger = logging.getLogger("app")

MAIN_SHEET_NAME = "bk_nodeman_info"

ANALYZE_ERROR_MSG = "第{}行：{}不能为空或格式错误，请依照模板填写，不要修改模板"


class ExcelHandler:
    @classmethod
    def generate_excel_template(cls):

        # 整合数据转为下拉框所需列表, [id]name 格式
        all_install_channel = [
            f"[{item['id']}]{item['name']}" for item in list(models.InstallChannel.objects.all().values())
        ]
        all_install_channel.insert(0, "[0]default")
        all_biz = [
            f"[{item['bk_biz_id']}]{item['bk_biz_name']}"
            for item in CmdbHandler().biz(param={"action": "agent_operate"})
        ]
        all_cloud = [
            f"[{item['bk_cloud_id']}]{item['bk_cloud_name']}" for item in list(models.Cloud.objects.all().values())
        ]
        all_cloud.insert(0, f"[{constants.DEFAULT_CLOUD}]{constants.DEFAULT_CLOUD_NAME}")
        all_ap = [f"[{item['id']}]{item['name']}" for item in list(models.AccessPoint.objects.all().values())]

        all_os = list(constants.OsType)
        all_auth_type = [str(type) for type in constants.ExcelAuthType.get_member_value__alias_map().values()]
        all_addressing = [str(type) for type in constants.CmdbAddressingType.get_member_value__alias_map().values()]
        all_enable_compression = ["True", "False"]

        # 生成excel模板
        excel = Workbook()
        excel_sheet = excel.active
        excel_sheet.title = MAIN_SHEET_NAME

        excel_field: Dict[Any, str] = constants.ExcelField.get_member_value__alias_map()
        excel_field_list = list(excel_field.keys())
        for col, key in enumerate(excel_field_list, start=1):
            title_row_cell = excel_sheet.cell(row=1, column=col, value=str(excel_field[key]))
            ExcelTools.set_font_style(title_row_cell, font_size=16, color="538DD5", bold=True)

            key_row_cell = excel_sheet.cell(row=2, column=col, value=str(key))
            ExcelTools.set_font_style(key_row_cell, font_size=12, color="538DD5", bold=True)

            optional_row_cell = excel_sheet.cell(row=3, column=col, value=constants.EXCEL_TITLE_OPTIONAL[key])
            if constants.EXCEL_TITLE_OPTIONAL[key] == constants.EXCEL_REQUIRED:
                ExcelTools.set_font_style(optional_row_cell, font_size=12, color="C0504D")
            else:
                ExcelTools.set_font_style(optional_row_cell, font_size=12, color="E26B0A")

            describe_row_cell = excel_sheet.cell(row=4, column=col, value=constants.EXCEL_TITLE_DESCRIBE[key])
            ExcelTools.set_font_style(describe_row_cell, font_size=12, color="000000")

            if key == constants.ExcelField.OS_TYPE.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_os)
            elif key == constants.ExcelField.INSTALL_CHANNEL.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_install_channel)
            elif key == constants.ExcelField.AUTH_TYPE.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_auth_type)
            elif key == constants.ExcelField.BIZ.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_biz)
            elif key == constants.ExcelField.CLOUD.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_cloud)
            elif key == constants.ExcelField.AP.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_ap)
            elif key == constants.ExcelField.ADDRESS_TYPE.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_addressing)
            elif key == constants.ExcelField.DATA_COMPRESSION.value:
                ExcelTools.create_dropdown(excel, 5, col, key, MAIN_SHEET_NAME, all_enable_compression)
            else:
                pass

        ExcelTools.fill_color(excel_sheet, 1, 4, 1, len(excel_field_list), "D9D9D9")
        ExcelTools.adjust_row_height(excel_sheet, 1, 3, 20)
        ExcelTools.adjust_row_height(excel_sheet, 4, 4, 115)
        ExcelTools.adjust_col_width(excel_sheet, 1, len(excel_field_list), 35)
        ExcelTools.set_alignment(excel_sheet, "center", "left")

        return excel

    def analyze_excel(self, file: InMemoryUploadedFile) -> List[Dict]:

        # 解析excel
        excel = load_workbook(filename=file)
        excel_sheet = excel.active
        keys = [cell.value for cell in excel_sheet[2]]

        # 正则匹配处理 [id]name 类型的下拉框内容
        pattern = r"\[(\d+)\]"

        # 获取加密cipher
        cipher = HostTools.get_asymmetric_cipher()

        required_list = [
            key for key, value in constants.EXCEL_TITLE_OPTIONAL.items() if value == constants.EXCEL_REQUIRED
        ]

        error_message: List[str] = []
        excel_data = []
        for index, row in enumerate(excel_sheet.iter_rows(min_row=5, values_only=True), start=5):

            row_data = {keys[i]: cell for i, cell in enumerate(row)}

            row_err_msg: List[str] = []

            if (
                row_data[constants.ExcelField.INNER_IPV4.value] is None
                and row_data[constants.ExcelField.INNER_IPV6.value] is None
            ):
                row_err_msg.append(ANALYZE_ERROR_MSG.format(index, "IP"))

            for key in required_list:
                if row_data[key] is None:
                    row_err_msg.append(ANALYZE_ERROR_MSG.format(index, key))

            if row_data[constants.ExcelField.INSTALL_CHANNEL.value] is not None:
                install_channel = re.findall(pattern, row_data[constants.ExcelField.INSTALL_CHANNEL.value])
                if not install_channel:
                    row_err_msg.append(ANALYZE_ERROR_MSG.format(index, constants.ExcelField.INSTALL_CHANNEL.value))
                row_data[constants.ExcelField.INSTALL_CHANNEL.value] = int(install_channel[0])

            if row_data[constants.ExcelField.BIZ.value] is not None:
                biz = re.findall(pattern, row_data[constants.ExcelField.BIZ.value])
                if not biz:
                    row_err_msg.append(ANALYZE_ERROR_MSG.format(index, constants.ExcelField.BIZ.value))
                row_data[constants.ExcelField.BIZ.value] = int(biz[0])

            if row_data[constants.ExcelField.CLOUD.value] is not None:
                cloud = re.findall(pattern, row_data[constants.ExcelField.CLOUD.value])
                if not cloud:
                    row_err_msg.append(ANALYZE_ERROR_MSG.format(index, constants.ExcelField.CLOUD.value))
                row_data[constants.ExcelField.CLOUD.value] = int(cloud[0])

            if row_data[constants.ExcelField.AP.value] is not None:
                ap = re.findall(pattern, row_data[constants.ExcelField.AP.value])
                if not ap:
                    row_err_msg.append(ANALYZE_ERROR_MSG.format(index, constants.ExcelField.AP.value))
                row_data[constants.ExcelField.AP.value] = int(ap[0])

            if len(row_err_msg) > 0:
                error_message.extend(row_err_msg)
                continue

            credentials: str = str(row_data[constants.ExcelField.CREDENTIALS.value])
            if (
                row_data[constants.ExcelField.AUTH_TYPE.value]
                == constants.ExcelAuthType.get_member_value__alias_map()[constants.ExcelAuthType.PASSWORD.value]
            ):
                row_data[constants.ExcelField.AUTH_TYPE.value] = constants.ExcelAuthType.PASSWORD.value
                row_data["password"] = HostTools.encrypt_with_friendly_exc_handle(cipher, credentials, ValueError)
            else:
                row_data[constants.ExcelField.AUTH_TYPE.value] = constants.ExcelAuthType.KEY.value
                row_data["key"] = HostTools.encrypt_with_friendly_exc_handle(cipher, credentials, ValueError)

            del row_data[constants.ExcelField.CREDENTIALS.value]

            if (
                row_data[constants.ExcelField.ADDRESS_TYPE.value]
                == constants.CmdbAddressingType.get_member_value__alias_map()[constants.CmdbAddressingType.STATIC.value]
            ):
                row_data[constants.ExcelField.ADDRESS_TYPE.value] = constants.CmdbAddressingType.STATIC.value
            else:
                row_data[constants.ExcelField.ADDRESS_TYPE.value] = constants.CmdbAddressingType.DYNAMIC.value

            excel_data.append(row_data)

        res = {"host": excel_data, "error_message": error_message}
        return res
