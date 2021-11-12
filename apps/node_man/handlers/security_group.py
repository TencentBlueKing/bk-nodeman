# -*- coding: utf-8 -*-
import abc
from typing import Dict, List, Optional

from django.conf import settings

from apps.node_man.exceptions import ConfigurationPolicyError
from apps.node_man.policy.tencent_vpc_client import VpcClient
from common.api import SopsApi


class BaseSecurityGroupFactory(abc.ABC):
    SECURITY_GROUP_TYPE = None

    def describe_security_group_address(self) -> List[str]:
        """获取安全组IP地址"""
        raise NotImplementedError()

    def add_ips_to_security_group(self, ip_list: List[str]) -> Dict:
        """添加IP到安全组中，输出的字典用作check_result的入参"""
        raise NotImplementedError()

    def check_result(self, ip_list: List[str]) -> bool:
        """检查IP列表是否已添加到安全组中"""
        raise NotImplementedError()


class SopsSecurityGroupFactory(BaseSecurityGroupFactory):
    SECURITY_GROUP_TYPE = "SOPS"

    def describe_security_group_address(self):
        pass

    def add_ips_to_security_group(self, ip_list: List[str]) -> Dict:
        task_id = SopsApi.create_task(
            {
                "name": "NodeMan Configure SecurityGroup",
                "template_id": settings.BKAPP_EE_SOPS_TEMPLATE_ID,
                "bk_biz_id": settings.BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID,
                "bk_username": settings.BKAPP_REQUEST_EE_SOPS_OPERATOR,
                "constants": {"${iplist}": ",".join(ip_list)},
            }
        )
        SopsApi.start_task(
            {
                "task_id": task_id,
                "bk_biz_id": settings.BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID,
                "bk_username": settings.BKAPP_REQUEST_EE_SOPS_OPERATOR,
            }
        )
        return {"task_id": task_id}

    def check_result(self, add_ip_output: Dict) -> bool:
        # 标准运维执行，只要任务成功完成则认为添加成功，由标准运维原子来保证可靠性
        state = SopsApi.get_task_status(
            {
                "task_id": add_ip_output["task_id"],
                "bk_biz_id": settings.BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID,
                "bk_username": settings.BKAPP_REQUEST_EE_SOPS_OPERATOR,
            }
        )["state"]
        return state == "FINISHED"


class TencentVpcSecurityGroupFactory(BaseSecurityGroupFactory):
    SECURITY_GROUP_TYPE = "TENCENT"

    def describe_security_group_address(self) -> List:
        client = VpcClient()
        ip_set = set()
        for template in client.ip_templates:
            if not ip_set:
                ip_set = client.describe_address_templates(template)
            else:
                # 取交集，表示多个安全组策略同时都已写入的IP
                ip_set = ip_set & set(client.describe_address_templates(template))
        return list(ip_set)

    def add_ips_to_security_group(self, ip_list: List[str]):
        client = VpcClient()
        for template in client.ip_templates:
            using_ip_list = client.describe_address_templates(template)
            # tencent vpc client只支持修改，因此这里先取出已有IP再加上新增的，构成最终安全组的IP
            final_ip_list = list(set(using_ip_list + ip_list))
            is_ok, message = client.add_ip_to_template(template, final_ip_list)
            if not is_ok:
                raise ConfigurationPolicyError(message)
        return {"ip_list": ip_list}

    def check_result(self, add_ip_output: Dict) -> bool:
        """检查IP列表是否已添加到安全组中"""
        current_ip_list = set(self.describe_security_group_address())
        # 需添加的IP列表是已有IP的子集，则认为已添加成功
        return set(add_ip_output["ip_list"]).issubset(set(current_ip_list))


def get_security_group_factory(security_group_type: Optional[str]) -> BaseSecurityGroupFactory:
    """获取安全组工厂，返回None表示无需配置安全组"""
    factory_map = {factory.SECURITY_GROUP_TYPE: factory for factory in BaseSecurityGroupFactory.__subclasses__()}
    factory = factory_map.get(security_group_type)
    if factory:
        return factory()
