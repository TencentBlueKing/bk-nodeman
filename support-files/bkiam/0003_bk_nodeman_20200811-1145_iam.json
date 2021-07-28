{
    "system_id": "bk_nodeman",
    "operations": [
        {
            "operation": "upsert_system",
            "data": {
                "id": "bk_nodeman",
                "name": "节点管理",
                "name_en": "nodeman",
                "description": "",
                "description_en": "",
                "clients": "bk_nodeman,bk_bknodeman",
                "provider_config": {"host": "http://__BK_NODEMAN_API_ADDR__", "auth": "basic"}
            }
        },
        {
            "operation": "upsert_resource_type",
            "data": {
                "id": "cloud",
                "name": "云区域",
                "name_en": "cloud area",
                "description": "",
                "description_en": "",
                "provider_config": {
                    "path": "/api/iam/v1/cloud"
                },
                "version": 1
            }
        },
        {
            "operation": "upsert_resource_type",
            "data": {
                "id": "ap",
                "name": "接入点",
                "name_en": "Access Point",
                "description": "",
                "description_en": "",
                "provider_config": {
                    "path": "/api/iam/v1/ap"
                },
                "version": 1
            }
        },
        {
            "operation": "upsert_resource_type",
            "data": {
                "id": "global_settings",
                "name": "全局配置",
                "name_en": "Global Settings",
                "description": "",
                "description_en": "",
                "provider_config": {
                    "path": "/api/iam/v1/gs"
                },
                "version": 1
            }
        },
        {
            "operation": "upsert_instance_selection",
            "data": {
                "id": "cloud_instance_selection",
                "name": "云区域",
                "name_en": "Cloud",
                "resource_type_chain": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "cloud"
                    }
                ]
            }
        },
        {
            "operation": "upsert_instance_selection",
            "data": {
              "id": "ap_instance_selection",
              "name": "接入点",
              "name_en": "Access Point",
              "resource_type_chain": [{"system_id": "bk_nodeman", "id": "ap"}]
          }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "cloud_view",
                "name": "云区域查看",
                "name_en": "Cloud View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "cloud",
                        "name_alias": "",
                        "name_alias_en": "",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_nodeman",
                                "id": "cloud_instance_selection"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "cloud_edit",
                "name": "云区域编辑",
                "name_en": "Cloud Edit",
                "description": "",
                "description_en": "",
                "type": "edit",
                "version": 1,
                "related_actions": [
                    "cloud_view"
                ],
                "related_resource_types": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "cloud",
                        "name_alias": "",
                        "name_alias_en": "",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_nodeman",
                                "id": "cloud_instance_selection"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "cloud_delete",
                "name": "云区域删除",
                "name_en": "Cloud Delete",
                "description": "",
                "description_en": "",
                "type": "delete",
                "version": 1,
                "related_actions": [
                    "cloud_view"
                ],
                "related_resource_types": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "cloud",
                        "name_alias": "",
                        "name_alias_en": "",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_nodeman",
                                "id": "cloud_instance_selection"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "cloud_create",
                "name": "云区域创建",
                "name_en": "Cloud Create",
                "description": "",
                "description_en": "",
                "type": "create",
                "version": 1
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "ap_view",
                "name": "接入点查看",
                "name_en": "Ap View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "ap",
                        "name_alias": "",
                        "name_alias_en": "",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_nodeman",
                                "id": "ap_instance_selection"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "ap_edit",
                "name": "接入点编辑",
                "name_en": "Ap Edit",
                "description": "",
                "description_en": "",
                "type": "edit",
                "version": 1,
                "related_actions": [
                    "ap_view"
                ],
                "related_resource_types": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "ap",
                        "name_alias": "",
                        "name_alias_en": "",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_nodeman",
                                "id": "ap_instance_selection"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "ap_delete",
                "name": "接入点删除",
                "name_en": "Ap Delete",
                "description": "",
                "description_en": "",
                "type": "delete",
                "version": 1,
                "related_actions": [
                    "ap_view"
                ],
                "related_resource_types": [
                    {
                        "system_id": "bk_nodeman",
                        "id": "ap",
                        "name_alias": "",
                        "name_alias_en": "",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_nodeman",
                                "id": "ap_instance_selection"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "ap_create",
                "name": "接入点创建",
                "name_en": "Ap Create",
                "description": "",
                "description_en": "",
                "type": "create",
                "version": 1
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "globe_task_config",
                "name": "任务配置",
                "name_en": "Globe Task Config",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "agent_view",
                "name": "Agent查询",
                "name_en": "Agent View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "id": "biz",
                        "system_id": "bk_cmdb",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_cmdb",
                                "id": "business"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "agent_operate",
                "name": "Agent操作",
                "name_en": "Agent Operate",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "id": "biz",
                        "system_id": "bk_cmdb",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_cmdb",
                                "id": "business"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "proxy_operate",
                "name": "Proxy操作",
                "name_en": "Proxy Operate",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "id": "biz",
                        "system_id": "bk_cmdb",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_cmdb",
                                "id": "business"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "plugin_view",
                "name": "插件查看",
                "name_en": "Plugin View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "id": "biz",
                        "system_id": "bk_cmdb",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_cmdb",
                                "id": "business"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "plugin_operate",
                "name": "插件操作",
                "name_en": "Plugin Operate",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "id": "biz",
                        "system_id": "bk_cmdb",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_cmdb",
                                "id": "business"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action",
            "data": {
                "id": "task_history_view",
                "name": "任务历史查看",
                "name_en": "Task History view",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": [
                    {
                        "id": "biz",
                        "system_id": "bk_cmdb",
                        "selection_mode": "instance",
                        "related_instance_selections": [
                            {
                                "system_id": "bk_cmdb",
                                "id": "business"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "operation": "upsert_action_groups",
            "data": [
                {
                    "name": "常规功能",
                    "name_en": "Normal",
                    "sub_groups": [
                        {
                            "name": "Agent管理",
                            "name_en": "Agent",
                            "actions": [
                                {
                                    "id": "agent_view"
                                },
                                {
                                    "id": "agent_operate"
                                }
                            ]
                        },
                        {
                            "name": "云区域管理",
                            "name_en": "Cloud Area",
                            "actions": [
                                {
                                    "id": "cloud_create"
                                },
                                {
                                    "id": "cloud_edit"
                                },
                                {
                                    "id": "cloud_delete"
                                },
                                {
                                    "id": "cloud_view"
                                },
                                {
                                    "id": "proxy_operate"
                                }
                            ]
                        },
                        {
                            "name": "插件管理",
                            "name_en": "Plugin",
                            "actions": [
                                {
                                    "id": "plugin_view"
                                },
                                {
                                    "id": "plugin_operate"
                                }
                            ]
                        },
                        {
                            "name": "任务历史",
                            "name_en": "Task History",
                            "actions": [
                                {
                                    "id": "task_history_view"
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "全局配置",
                    "name_en": "Globle Configuration",
                    "sub_groups": [
                        {
                            "name": "接入点管理",
                            "name_en": "Access Point",
                            "actions": [{"id": "ap_create"}, {"id": "ap_delete"}, {"id": "ap_edit"}, {"id": "ap_view"}]
                        },
                        {
                            "name": "任务配置",
                            "name_en": "Task Configuration",
                            "actions": [{"id": "globe_task_config"}]
                        }
                    ]
                }
            ]
        },
        {
            "operation": "upsert_resource_creator_actions",
            "data": {
                "config": [
                    {
                        "id": "ap",
                        "actions": [
                            {"id": "ap_edit", "required": false},
                            {"id": "ap_view", "required": false},
                            {"id": "ap_delete", "required": false}
                        ]
                    },
                    {
                        "id": "cloud",
                        "actions": [
                            {"id": "cloud_edit", "required": false},
                            {"id": "cloud_view", "required": false},
                            {"id": "cloud_delete", "required": false}
                        ]
                    }
                ]
            }
        }
    ]
}
