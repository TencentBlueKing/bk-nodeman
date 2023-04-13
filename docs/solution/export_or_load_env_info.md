# 节点管理导入导出说明
>容器化环境操作时，可以通过 `kubctl cp `复制导入时所需数据文件
## 导出

### 导出脚本使用说明
> 通过脚本链接外部数据库，将节点管理所需数据放到文件中保存，并且在导入时需要对应的导出文件数据

*脚本依赖第三方库  pymysql*

安装方式： 
```bash
pip install pymysql
```
- 脚本名称：`export_host_info.py`
- 项目内脚本相对路径：`scripts/load_or_export_host_info/export_host_info.py`
- 脚本参数

```bash
  --host HOST          MySQL Target Ip   # mysql数据库链接地址
  --account ACCOUNT    MySQL account     # mysql数据库账号
  --password PASSWORD  MySQL password    # mysql 数据库密码
  --port PORT          MySQL port        # mysql 数据库链接端口
  --dbname DBNAME      NodeMan Database Name # 节点管理导出数据库名
  --only-cloud         Only export cloud info # 只导出云区域数据
  --only-proxy         Only export proxy host info  # 只导出 Proxy 主机数据
  --with-v6-field      Export proxy host info with ipv6 fields # 是否导出 v6 相关字段，默认不导出
```
- 导出文件路径 ：
	- 云区域文件路径：`node_man_export/cloud_info.csv`
	- 主机文件路径：`node_man_export/proxy_host_info.csv`
	-  `node_man_export` 位于脚本所在当前目录

#### 详细日志

*日志文件保存的日志基本为 DEBUG , 日志文件路径在  `node_man_export` 目录中，按照时间排序*

#### 使用示例

```bash
# 全部导出
python export_host_info.py --host 127.0.0.1 --port 3306 --password blueking --dbname bk_nodeman 

# 只导出 Proxy 主机数据
python export_host_info.py --host 127.0.0.1 --port 3306 --password blueking --dbname bk_nodeman --only-proxy

# 只导出 Cloud 云区域数据
python export_host_info.py --host 127.0.0.1 --port 3306 --password blueking --dbname bk_nodeman --only-cloud

# 只导出 Proxy 主机数据，附带 V6 主机字段
python export_host_info.py --host 127.0.0.1 --port 3306 --password blueking --dbname bk_nodeman --only-proxy --with-v6-field
```

## 导入


### 导入脚本使用说明
> 导入脚本属于项目内的 `django command` ，通过链接外部数据库读取映射数据，并根据导出文件内的数据，调整节点管理导入数据

*导入脚本无第三方依赖，可以直接使用*

#### 参数说明
```bash
  --is_switch_env_ap    export another env info file path
  --is_migrate_proxy_info
                        export another env info file path
  --env_name ENV_NAME   导出环境名称
  --bk_biz_ids BK_BIZ_IDS
                        当前环境中需要迁移的业务 ID 列表, 格式: '1,2,3'
  --mysql_host MYSQL_HOST
                        公共数据库地址
  --mysql_port MYSQL_PORT
                        公共数据库端口
  --mysql_user MYSQL_USER
                        公共数据库用户
  --mysql_db MYSQL_DB   公共数据库链接库名称
  --mysql_password MYSQL_PASSWORD
                        公共数据库密码
  --env_offset_table ENV_OFFSET_TABLE
                        环境映射表
  --env_biz_map_table ENV_BIZ_MAP_TABLE
                        业务映射表
  --old_ap__new_ap_map OLD_AP__NEW_AP_MAP
                        导出环境接入点与当前接入点映射关系, 格式: '1:2,2:3'
  --cloud_file_path CLOUD_FILE_PATH
                        导出环境云区域信息文件路径
  --proxy_file_path PROXY_FILE_PATH
                        导出环境 Proxy 主机信息文件路径
```

old_ap__new_ap_map:   导出环境接入点 ID 与当前环境接入点 ID 映射关系，格式为: `'-1:-1,1:2,2:3'`，这里需要主机接入点 ID 为 -1 时，属于自动选择接入点的接入点 ID

bk_biz_ids：指定的迁移当前环境业务 ID 范围，格式为: 1,2,3

#### 使用示例
```bash
# 定位业务 ID 为 38 的 Proxy 主机
python manage.py load_env_info --env_name="test_load.com" --bk_biz_ids=1,2,3  --mysql_host=127.0.0.1 --mysql_password=12345  --mysql_port=3306  --old_ap__new_ap_map='-1:-1,1:2,2:3' --cloud_file_path='/app/scripts/load_or_export_host_info/node_man_export/cloud_info.csv' --proxy_file_path='/app/scripts/load_or_export_host_info/node_man_export/proxy_host_info.csv' --is_migrate_proxy_info 


# 切换环境内的所有云区域接入点信息，并且切换业务 ID 为38的业务内并且属于相关云区域下的的所有主机接入点
python manage.py load_env_info --env_name="test_load.com" --bk_biz_ids=1,2,3  --mysql_host=127.0.0.1 --mysql_password=12345 --mysql_port=3306  --old_ap__new_ap_map='-1:-1,1:2,2:3' --cloud_file_path='/app/scripts/load_or_export_host_info/node_man_export/cloud_info.csv' --proxy_file_path='/app/scripts/load_or_export_host_info/node_man_export/proxy_host_info.csv' --is_switch_env_ap

```


### 第三方插件导入

```bash

# 1. 复制插件包到容器
PKG_NAME="nodeman_upload_o_bk-2023-04-18.tar.gz"

export FIRST_RUNNING_POD=$(kubectl get pods -n blueking \
  --selector=app.kubernetes.io/instance=bk-nodeman --field-selector=status.phase=Running \
  -o custom-columns=":metadata.name" | sed '/^$/d' | head -n 1 )

kubectl cp ${PKG_NAME}  -n blueking ${FIRST_RUNNING_POD}:/app/official_plugin/

# 2. 登录容器 ID 为${FIRST_RUNNING_POD}

# 3. 检查插件包是否上传并且解压
ll /app/official_plugin/${FIRST_RUNNING_POD}
cd /app/offical_plugin/ && tar xvf ${PKG_NAME}

# 4. 执行迁移命令
python manage.py init_official_plugins

```