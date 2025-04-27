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
import os

import ujson as json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.vpc.v20170312 import models, vpc_client

from apps.node_man.exceptions import ConfigurationPolicyError
from common.log import logger


class VpcClient(object):
    def __init__(self, region="ap-guangzhou", profile=None):
        self.region = region
        self.client = None
        self.tencent_secret_id = os.getenv("TXY_SECRETID")
        self.tencent_secret_key = os.getenv("TXY_SECRETKEY")
        self.ip_templates = os.getenv("TXY_IP_TEMPLATES", "")

        # 配置文件包含敏感信息，不需要的环境需要注意去掉
        if not all([self.tencent_secret_id, self.tencent_secret_key]):
            raise ConfigurationPolicyError("Please contact maintenaner to check Tencent cloud configuration.")

        # 将字符串变量转换为列表
        self.ip_templates = self.ip_templates.split(",")
        cred = credential.Credential(self.tencent_secret_id, self.tencent_secret_key)
        self.client = vpc_client.VpcClient(cred, self.region, profile)

    def describe_address_templates(self, template_name):
        req = models.DescribeAddressTemplatesRequest()
        params = {"Filters": [{"Name": "address-template-id", "Values": [template_name]}]}
        req.from_json_string(json.dumps(params))
        resp = self.client.DescribeAddressTemplates(req)
        result = json.loads(resp.to_json_string())
        if result["TotalCount"] != 1:
            logger.error(f"tencent_cloud_describe_address_templates result: {result}")
            raise TencentCloudSDKException(
                "QueryTemplateFailed", "Querying the current ip template failed", result.get("RequestId")
            )
        return result["AddressTemplateSet"][0]["AddressSet"]

    def add_ip_to_template(self, template_name, ip_list):
        try:
            req = models.ModifyAddressTemplateAttributeRequest()
            params = {"AddressTemplateId": template_name, "Addresses": ip_list}
            req.from_json_string(json.dumps(params))
            resp = self.client.ModifyAddressTemplateAttribute(req)
            result = json.loads(resp.to_json_string())
            logger.info(f"tencent_cloud_add_ip_to_template: {result}")
            return True, f"request_id: {result.get('RequestId')}"
        except TencentCloudSDKException as err:
            if err.code == "InvalidParameterValue.Duplicate":
                return True, err.message
            return False, err

    def CreateSecurityGroupPolicies(self, sg_id, policies):
        """本接口（CreateSecurityGroupPolicies）用于创建安全组规则（SecurityGroupPolicy）。"""
        try:
            req = models.CreateSecurityGroupPoliciesRequest()
            params = {"SecurityGroupId": sg_id, "SecurityGroupPolicySet": policies}
            req.from_json_string(json.dumps(params))
            resp = self.client.CreateSecurityGroupPolicies(req)
            result = json.loads(resp.to_json_string())
            logger.info(f"create_security_group_policies: {result}")
            return True, f"request_id: {result.get('RequestId')}"
        except TencentCloudSDKException as err:
            if err.code == "InvalidParameterValue.Duplicate":
                return True, err.message
            return False, err

    def DescribeSecurityGroupPolicies(self, sg_id):
        """本接口（DescribeSecurityGroupPolicies）用于查询安全组规则（SecurityGroupPolicy）。"""
        try:
            req = models.DescribeSecurityGroupPoliciesRequest()
            params = {"SecurityGroupId": sg_id}
            req.from_json_string(json.dumps(params))
            resp = self.client.DescribeSecurityGroupPolicies(req)
            result = json.loads(resp.to_json_string())
            logger.info(f"describe_security_group_policies: {result}")
            return True, result
        except TencentCloudSDKException as err:
            if err.code == "InvalidParameterValue.Duplicate":
                return True, err.message
            return False, err
