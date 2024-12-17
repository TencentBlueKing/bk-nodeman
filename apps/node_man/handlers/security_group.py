# -*- coding: utf-8 -*-
import abc
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from apps.backend.utils.dataclass import asdict
from apps.node_man.exceptions import (
    ConfigurationPolicyError,
    TXYPolicyConfigNotExistsError,
    YunTiPolicyConfigNotExistsError,
)
from apps.node_man.models import GlobalSettings
from apps.node_man.policy.tencent_vpc_client import VpcClient
from apps.utils.batch_request import request_multi_thread
from common.api import SopsApi, YunTiApi
from common.log import logger


@dataclass
class YunTiPolicyData:
    Protocol: str
    CidrBlock: str
    Port: str
    Action: str
    PolicyDescription: Optional[str] = None
    Ipv6CidrBlock: Optional[str] = None


@dataclass
class YunTiPolicyConfig:
    dept_id: int
    region: str
    sid: str
    group_name: str
    port: str
    action: str
    protocol: str


@dataclass
class TXYPolicyConfig:
    region: str
    sid: str
    port: str
    action: str
    protocol: str


@dataclass
class TXYPolicyData:
    Protocol: str
    CidrBlock: str
    Port: str
    Action: str
    PolicyDescription: Optional[str] = None
    Ipv6CidrBlock: Optional[str] = None


class BaseSecurityGroupFactory(abc.ABC):
    SECURITY_GROUP_TYPE = None

    def describe_security_group_address(self) -> List[str]:
        """获取安全组IP地址"""
        raise NotImplementedError()

    def add_ips_to_security_group(self, ip_list: List[str], creator: str = None) -> Dict:
        """添加IP到安全组中，输出的字典用作check_result的入参"""
        raise NotImplementedError()

    def check_result(self, ip_list: List[str]) -> bool:
        """检查IP列表是否已添加到安全组中"""
        raise NotImplementedError()


class SopsSecurityGroupFactory(BaseSecurityGroupFactory):
    SECURITY_GROUP_TYPE = "SOPS"

    def describe_security_group_address(self):
        pass

    def add_ips_to_security_group(self, ip_list: List[str], creator: str = None) -> Dict:
        task_id = SopsApi.create_task(
            {
                "name": "NodeMan Configure SecurityGroup",
                "template_id": settings.BKAPP_EE_SOPS_TEMPLATE_ID,
                "bk_biz_id": settings.BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID,
                "bk_username": settings.BKAPP_REQUEST_EE_SOPS_OPERATOR,
                "constants": {"${ip_list}": " ".join(ip_list)},
            }
        )["task_id"]
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

    def add_ips_to_security_group(self, ip_list: List[str], creator: str = None):
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


class YunTiSecurityGroupFactory(BaseSecurityGroupFactory):
    SECURITY_GROUP_TYPE: str = "YUNTI"

    def __init__(self) -> None:
        """
        policies_config: example
        [
            {
                "dept_id": 0,
                "region": "ap-xxx",
                "sid": "xxxx",
                "group_name": "xxx",
                "port": "ALL",
                "action": "ACCEPT",
                "protocol": "ALL",
                ""
            }
        ]
        """
        self.policy_configs: List[Dict[str, Any]] = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.YUNTI_POLICY_CONFIGS.value, default=[]
        )
        if not self.policy_configs:
            raise YunTiPolicyConfigNotExistsError()

    def describe_security_group_address(self) -> Dict:
        # 批量获取当前安全组策略详情
        params_list: List = []
        for policy_config in self.policy_configs:
            config = YunTiPolicyConfig(**policy_config)
            params_list.append(
                {
                    "params": {
                        "method": "get-security-group-policies",
                        "params": {
                            "deptId": config.dept_id,
                            "region": config.region,
                            "sid": config.sid,
                        },
                        "no_request": True,
                    },
                }
            )
        # 批量请求
        result: List[Dict[str, Any]] = request_multi_thread(
            func=YunTiApi.get_security_group_details,
            params_list=params_list,
            get_data=lambda x: [x],
        )
        return {sid_info["SecurityGroupId"]: sid_info for sid_info in result}

    def add_ips_to_security_group(self, ip_list: List[str], creator: str = None):
        result: Dict[str, Dict[str, Any]] = self.describe_security_group_address()
        params_list: List[Dict[str, Any]] = []

        for policy_config in self.policy_configs:
            config = YunTiPolicyConfig(**policy_config)
            # 新策略列表
            new_in_gress: Dict[str, Dict[str, Any]] = {}
            for ip in ip_list:
                new_in_gress[ip] = asdict(
                    YunTiPolicyData(
                        Protocol=config.protocol,
                        CidrBlock=ip,
                        Port=config.port,
                        Action=config.action,
                        PolicyDescription=f"Add by {creator}",
                        Ipv6CidrBlock="",
                    )
                )

            version: str = result[config.sid]["pilicies"]["SecurityGroupPolicySet"]["Version"]
            current_policies: List[Dict[str, Any]] = result[config.sid]["pilicies"]["SecurityGroupPolicySet"]["Ingress"]

            # 已有策略列表
            in_gress: Dict[str, Dict[str, Any]] = {}
            for policy in current_policies:
                in_gress[policy["CidrBlock"]] = asdict(
                    YunTiPolicyData(
                        Protocol=policy["Protocol"],
                        CidrBlock=policy["CidrBlock"],
                        Port=policy["Port"],
                        Action=policy["Action"],
                        PolicyDescription=policy["PolicyDescription"],
                        Ipv6CidrBlock=policy["Ipv6CidrBlock"],
                    )
                )
            # 增加新IP
            in_gress.update(new_in_gress)

            params_list.append(
                {
                    "params": {
                        "method": "createSecurityGroupForm",
                        "params": {
                            "deptId": config.dept_id,
                            "region": config.region,
                            "sid": config.sid,
                            "type": "modify",
                            "mark": "Add proxy whitelist to Shangyun security group security.",
                            "groupName": config.group_name,
                            "groupDesc": "Proxy whitelist for Shangyun",
                            "creator": creator,
                            "ext": {
                                "Version": version,
                                "Egress": [],
                                "Ingress": list(in_gress.values()),
                            },
                        },
                        "no_request": True,
                    },
                }
            )
        # 批量请求
        logger.info(f"Add proxy whitelist to Shangyun security group security. params: {params_list}")
        request_multi_thread(func=YunTiApi.operate_security_group, params_list=params_list)
        return {"ip_list": ip_list}

    def check_result(self, add_ip_output: Dict) -> bool:
        """检查IP列表是否已添加到安全组中"""
        result: Dict[str, Dict[str, Any]] = self.describe_security_group_address()
        is_success: bool = True
        for policy_config in self.policy_configs:
            config = YunTiPolicyConfig(**policy_config)
            current_policies: List[Dict[str, Any]] = result[config.sid]["pilicies"]["SecurityGroupPolicySet"]["Ingress"]
            current_ip_list = [policy["CidrBlock"] for policy in current_policies]
            logger.info(
                f"check_result: Add proxy whitelist to Shangyun security group security. "
                f"sid: {config.sid} ip_list: {add_ip_output['ip_list']}"
            )
            # 需添加的IP列表是已有IP的子集，则认为已添加成功
            is_success: bool = is_success and set(add_ip_output["ip_list"]).issubset(set(current_ip_list))

        return is_success


class TXYSecurityGroupFactory(BaseSecurityGroupFactory):
    SECURITY_GROUP_TYPE: str = "TXY"

    def __init__(self) -> None:
        """
        policies_config: example
        [
            {
                "region": "ap-xxx",
                "sid": "xxxx",
                "port": "ALL",
                "action": "ACCEPT",
                "protocol": "ALL"
            }
        ]
        """
        self.policy_configs: List[Dict[str, Any]] = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.TXY_POLICY_CONFIGS.value, default=[]
        )
        if not self.policy_configs:
            raise TXYPolicyConfigNotExistsError()

        self.endpoint = settings.TXY_ENDPOINT

    @property
    def profile(self):
        httpProfile = HttpProfile()
        httpProfile.endpoint = self.endpoint

        # 设置客户端相关配置
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        return clientProfile

    def describe_security_group_address(self, client: VpcClient, sid: str) -> List[str]:
        is_ok, result = client.DescribeSecurityGroupPolicies(sid)
        if not is_ok:
            raise ConfigurationPolicyError(result)

        current_policies: List[Dict[str, Any]] = result["SecurityGroupPolicySet"]["Ingress"]
        current_ip_list = [policy["CidrBlock"] for policy in current_policies]
        return current_ip_list

    def add_ips_to_security_group(self, ip_list: List[str], creator: str = None):
        for policy_config in self.policy_configs:
            config = TXYPolicyConfig(**policy_config)
            new_in_gress: Dict[str, List[Dict[str, Any]]] = []
            client = VpcClient(config.region, self.profile)
            current_ip_list: List[str] = self.describe_security_group_address(client, config.sid)
            need_add_ip_list: set = set(ip_list) - set(current_ip_list)
            if need_add_ip_list:
                for ip in need_add_ip_list:
                    new_in_gress.append(
                        asdict(
                            TXYPolicyData(
                                Protocol=config.protocol,
                                CidrBlock=ip,
                                Port=config.port,
                                Action=config.action,
                                PolicyDescription=f"Add by {creator}",
                                Ipv6CidrBlock="",
                            )
                        )
                    )
                is_ok, message = client.CreateSecurityGroupPolicies(
                    sg_id=config.sid, policies={"Ingress": new_in_gress}
                )
                if not is_ok:
                    raise ConfigurationPolicyError(message)

        return {"ip_list": ip_list}

    def check_result(self, add_ip_output: Dict) -> bool:
        """检查IP列表是否已添加到安全组中"""
        is_success: bool = True
        for policy_config in self.policy_configs:
            config = TXYPolicyConfig(**policy_config)
            client = VpcClient(config.region, self.profile)
            current_ip_list: List[str] = self.describe_security_group_address(client, config.sid)
            logger.info(
                f"check_result: Add proxy whitelist to Shangyun security group security. "
                f"sid: {config.sid} ip_list: {add_ip_output['ip_list']}"
            )
            # 需添加的IP列表是已有IP的子集，则认为已添加成功
            is_success: bool = is_success and set(add_ip_output["ip_list"]).issubset(set(current_ip_list))

        return is_success


def get_security_group_factory(security_group_type: Optional[str]) -> BaseSecurityGroupFactory:
    """获取安全组工厂，返回None表示无需配置安全组"""
    factory_map = {factory.SECURITY_GROUP_TYPE: factory for factory in BaseSecurityGroupFactory.__subclasses__()}
    factory = factory_map.get(security_group_type)
    if factory:
        return factory()
