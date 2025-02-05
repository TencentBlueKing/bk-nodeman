#!/bin/ksh
# vim:ft=sh expandtab sts=4 ts=4 sw=4 nu
# gse agent安装脚本, 仅在节点管理2.0中使用

# DEFAULT DEFINITION
NODE_TYPE=agent
# PKG_NAME=gse_client-aix{version}-powerpc.tgz
PKG_NAME=""
OS_VERSION=""

GSE_AGENT_RUN_DIR=/var/run/gse
GSE_AGENT_DATA_DIR=/var/lib/gse
GSE_AGENT_LOG_DIR=/var/log/gse
set -A BACKUP_CONFIG_FILES "procinfo.json"

# 收到如下信号或者exit退出时，执行清理逻辑
#trap quit 1 2 3 4 5 6 7 8 10 11 12 13 14 15
trap cleanup HUP INT QUIT ABRT SEGV PIPE ALRM TERM EXIT

report_step_status () {
    local date _time log_level step status message
    local tmp_json_body tmp_json_resp

    # 未设置上报API时，直接忽略
    [ -z "$CALLBACK_URL" ] && return 0

    echo "$@" | read  date _time log_level step status message

    tmp_time=$(date +%Y%m%d_%H%M%S)
    tmp_date=$(date +%s)
    touch "/tmp/nm.reqbody."$tmp_time"."$tmp_date".json"
    touch "/tmp/nm.reqresp."$tmp_time"."$tmp_date".json"
    tmp_json_body="/tmp/nm.reqbody."$tmp_time"."$tmp_date".json"
    tmp_json_resp="/tmp/nm.reqresp."$tmp_time"."$tmp_date".json"

    cat > "$tmp_json_body" <<_OO_
{
    "task_id": "$TASK_ID",
    "token": "$TOKEN",
    "logs": [
        {
            "timestamp": "$(date +%s)",
            "level": "$log_level",
            "step": "$step",
            "log": "$message",
            "status": "$status"
        }
    ]
}
_OO_
    http_proxy=$HTTP_PROXY https_proxy=$HTTP_PROXY \
        curl -s -S -X POST -d@"$tmp_json_body" "$CALLBACK_URL"/report_log/ -o "$tmp_json_resp"
    rm -f "$tmp_json_body" "$tmp_json_resp"
}

log ()  { local L=INFO D;  D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; return 0; }
warn () { local L=WARN D;  D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; return 0; }
err ()  { local L=ERROR D; D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; return 1; }
fail () { local L=ERROR D; D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; exit 1; }

divide_version () {
    result=$(oslevel)
    log report_os_version DONE "${result}"

    if echo "${result}" | egrep -q  '^6.*' ; then
        OS_VERSION=6
    elif  echo "${result}" | egrep -q  '^7.*' ; then
        OS_VERSION=7
    else
        fail check_env FAILED "unsupported OS version: ${result}"
    fi
    PKG_NAME=gse_client-aix"${OS_VERSION}"-powerpc.tgz
}

get_cpu_arch () {
    local cmd=$1
    CPU_ARCH=$($cmd)
    CPU_ARCH=$(echo ${CPU_ARCH} | tr 'A-Z' 'a-z')
    if [[ "$CPU_ARCH" == *x86_64* ]]; then
        return 0
    elif [[ "$CPU_ARCH" == *x86* ]]; then
        return 0
    elif [[ "$CPU_ARCH" == *aarch* ]]; then
        return 0
    elif [[ "$CPU_ARCH" == *powerpc* ]]; then
        return 0
    else
        return 1
    fi
}

get_cpu_arch "uname -p" || get_cpu_arch "uname -m" || fail get_cpu_arch FAILED "Failed to get CPU arch, please contact the developer."

# 清理逻辑：保留本次的LOG_FILE,下次运行时会删除历史的LOG_FILE。
# 保留安装脚本本身
cleanup () {
    local GLOBIGNORE="$LOG_FILE"
    rm -rf "$TMP_DIR"/nm.*

    exit 0
}

validate_setup_path () {
    set -A invalid_path_prefix /tmp /var /etc /bin /lib /lib64 /boot /mnt /proc /dev /run /sys /sbin /root

    set -A invalid_path /usr /usr/bin /usr/sbin /usr/local/lib /usr/include /usr/lib /usr/lib64 /usr/libexec


    local p1="${AGENT_SETUP_PATH%/$NODE_TYPE*}"
    local p2="${p1%/gse*}"
    local p p3

    if [[ "$p1" == "${AGENT_SETUP_PATH}" ]] || [[ "$p2" == "$AGENT_SETUP_PATH" ]]; then
        fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
    fi
    for p in "${invalid_path[@]}"; do
        if [[ "${p2}" == "$p" ]]; then
            fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
        fi
    done
    for p in "${invalid_path_prefix[@]}"; do
        p3=$(echo "$p2" |sed 's/$p/$p2/g')
        if [[ "$p3" != "$p2" ]]; then
            fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
        fi
    done
}

is_port_listen () {
    local BT_PORT_START=$1
    local BT_PORT_END=$2
    sleep 1

    while (("$BT_PORT_START" <= "$BT_PORT_END"))
    do
        netstat -aon |grep "${BT_PORT_START}" |grep LISTEN  2>/dev/null && return 0
        let BT_PORT_START = BT_PORT_START + 1
    done
    return 1
}

is_connected () {
    local i port=$1

    for i in {0..15}; do
        sleep 1
        netstat -aon |grep ${port} |grep ESTABLISHED 2>/dev/null && return 0
    done

    return 1
}

is_gsecmdline_ok () {
   /bin/gsecmdline -d 1430 -s test >/dev/null 2>&1
}

# 用法：通过ps的comm字段获取pid，pgid和pid相同是为gse_master
get_pid () {
    local proc=${1:-agent}

    pattern1=$(ps -eo pid,pgid,comm | grep gse_${proc} | sed -n 1p |awk '{print$1,$2}')
    pattern2=$(ps -eo pid,pgid,comm | grep gse_${proc} | sed -n 2p |awk '{print$1,$2}')

    set -A pids1 $pattern1
    set -A pids2 $pattern2

    if [[ ${pids1[0]} == ${pids1[1]} ]];then
        set -A gse_master ${pids1[0]}
        set -A gse_workers ${pids2[0]}
    elif [[ ${pids2[0]} == ${pids2[1]} ]];then
        set -A gse_master ${pids2[0]}
        set -A gse_workers ${pids1[0]}
    else
        echo 'no gse_Master'
    fi

    printf "%d\n" "${pids[@]}"
}

is_process_ok () {
    local proc=${1:-agent}

    sleep 5
    get_pid "$proc"

    if [ "${#gse_master[@]}" -eq 0 ]; then
        fail setup_agent FAILED "process check: no gseMaster found. gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    if [ "${#gse_master[@]}" -gt 1 ]; then
        fail setup_agent FAILED "process check: multi gseMaster found. gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    # worker 进程在某些任务情况下可能不只一个，只要都是一个爹，多个worker也是正常，不为0即可
    if [ "${#gse_workers[@]}" -eq 0 ]; then
        fail setup_agent FAILED "process check: ${proc}Worker not found (node type:$NODE_TYPE)"
    fi
}

is_target_reachable () {
    local ip=${1}
    local target_port=$2
    local _port err
    local i=0
	set -A target_port_arr

    target_port_t=$(echo "$target_port"|grep -E [0-9]+-[0-9])
    if [[ $? == 0 ]]; then
        target_port_1=$(echo "$target_port_t" | awk -F "-" '{print$1}')
        target_port_2=$(echo "$target_port_t" | awk -F "-" '{print$2}')
        if [[ $target_port_1 -lt $target_port_2 ]];then
            target_port_arr[$i]=$target_port_1
        fi
        let target_port_1=target_port_1+1
        let i=i+1
        #target_port=$(seq ${target_port//-/ })
    else
        set -A target_port_arr $target_port
	fi
    for _port in ${target_port_arr[@]}; do
        ksh -c  "telnet $ip $_port" 2>/dev/null
        case $? in
            0) return 0 ;;
            1) err="connection refused" ;;
            ## 超时的情况，只有要一个端口是超时的情况，认定为网络不通，不继续监测
            124) fail check_env FAILED "connect to upstream server($ip:$target_port) failed: NETWORK TIMEOUT" ;;
        esac
    done

    fail check_env FAILED "connect to upstream server($ip:$target_port) failed: $err" ;
}

## network policy check
check_polices_agent_to_upstream () {
    #local pagent_to_proxy_port_policies=(gse_task:48668 gse_data:58625 gse_btsvr:58925 gse_btsvr:10020-10030)
    #local pagent_listen_ports=(gse_agent:60020-60030)
    local ip

    # 非直连Agent的上级节点是所属管控区域的proxy
    for ip in "${TASK_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $DATA_PORT of $ip($UPSTREAM_TYPE)"
        is_target_reachable "$ip" "$IO_PORT"
    done

    for ip in "${DATA_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $DATA_PORT of $ip($UPSTREAM_TYPE)"
        is_target_reachable "$ip" "$DATA_PORT"
    done

    for ip in "${BT_FILE_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $FILE_SVR_PORT,$BT_PORT-$TRACKER_PORT of $ip($UPSTREAM_TYPE)"
        is_target_reachable "$ip" "$FILE_SVR_PORT"
        is_target_reachable "$ip" "$BT_PORT"-"$TRACKER_PORT"
    done
}

check_polices_pagent_to_upstream () {
    check_polices_agent_to_upstream
}

check_policies_proxy_to_upstream () {
    #local proxy_to_server_policies=(gse_task:48668 gse_data:58625 gse_btsvr:58930 gse_btsvr:10020-10030 gse_ops:58725)
    #local proxy_listen_ports=(gse_agent:48668 gse_transit:58625 gse_btsvr:58930 gse_btsvr:58925 gse_btsvr:10020-10030 gse_opts:58725)
    local ip

    # GSE Proxy 的上级节点可能是 GSE Server(不同的接入点), 也可能是一级Proxy节点
    for ip in "${TASK_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $IO_PORT of $ip(${UPSTREAM_TYPE:-GSE_SERVER})"
        is_target_reachable "$ip" "$IO_PORT"
    done

    for ip in "${DATA_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $DATA_PORT of $ip(${UPSTREAM_TYPE:-GSE_SERVER})"
        is_target_reachable "$ip" "$DATA_PORT"
    done

    for ip in "${BT_FILE_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $BTSVR_THRIFT_PORT of $ip(${UPSTREAM_TYPE:-GSE_SERVER})"
        is_target_reachable "$ip" "$BTSVR_THRIFT_PORT"
        is_target_reachable "$ip" "$BT_PORT"
    done
}

pre_view () {
   log PREVIEW - "---- precheck current deployed agent info ----"

   if [[ -f $AGENT_SETUP_PATH/etc/agent.conf ]]; then
       log PREVIEW - "normalized agent:"
       log PREVIEW - "   setup path: "${AGENT_SETUP_PATH}"/bin/gse_agent"
       log PREVIEW - "   process:"
       #lsof -a -d txt -c agentWorker -c gseMaster -a -n "$AGENT_SETUP_PATH"/bin/gse_agent
       # Aix 操作系统当前没有提供 gsecmdline 工具，暂不检查
       # log PREVIEW - "   gsecmdline: $(is_gsecmdline_ok && echo OK || echo NO)"
    fi
}

setup_crontab () {
    local tmpcron
    local datatemp=$(date +%s)

    crontab -l | grep -v "$AGENT_SETUP_PATH/bin/gsectl" >/tmp/cron.$datatemp
    echo "* * * * * $AGENT_SETUP_PATH/bin/gsectl watch >/dev/null 2>&1" >>/tmp/cron.$datatemp

    crontab /tmp/cron.$datatemp && rm -f /tmp/cron.$datatemp
}

remove_crontab () {

    if [ $IS_SUPER == false ]; then
        return
    fi

    local tmpcron
    local datatemp=$(date +%s)

    crontab -l | grep -v "$AGENT_SETUP_PATH/bin/gsectl" > /tmp/cron.$datatemp
    crontab /tmp/cron.$datatemp && rm -f /tmp/cron.$datatemp

    # 下面这段代码是为了确保修改的crontab能立即生效
    ps -eo pid,comm | grep cron |awk '{print$1}' | xargs kill -9
}

setup_startup_scripts () {
    if [ $IS_SUPER == false ]; then
        return
    fi

    local rcfile=/etc/rc.local

    if [ -f $rcfile ];then
        # 先删后加，避免重复
        #sed -i "\|${AGENT_SETUP_PATH}/bin/gsectl|d" $rcfile
        tmp_rcfile=$(grep -v "${AGENT_SETUP_PATH}/bin/gsectl")
        echo "$tmp_rcfile" >$rcfile
    else
	touch "$rcfile" && chmod 755 "$rcfile"
    fi

    echo "[ -f $AGENT_SETUP_PATH/bin/gsectl ] && $AGENT_SETUP_PATH/bin/gsectl start >/var/log/gse_start.log 2>&1" >>$rcfile
}

start_agent () {
    local i p

    "$AGENT_SETUP_PATH"/bin/gsectl start || fail setup_agent FAILED "start gse agent failed"

    sleep 3
    is_process_ok agent
}

remove_proxy_if_exists () {
    local i pids
    local path=${AGENT_SETUP_PATH%/*}/proxy

    ! [[ -d $path ]] && return 0
    "$path/bin/gsectl" stop

    for p in agent transit btsvr opts; do
        for i in {0..10}; do
            set -A pids $(ps -ef pid,comm | grep gse_"$p" | awk '{print$1}')
            if [ ${#pids[@]} -eq 0 ]; then
                # 进程已退，继续检查下一个进程
                break
            elif [ "$i" == 10 ]; then
                # 强杀
                kill -9 "${pids[@]}"
            else
                sleep 1
            fi
        done
    done

    rm -rf "$path"
}

stop_agent () {
    local i pids
    ! [[ -d $AGENT_SETUP_PATH ]] && return 0
    "$AGENT_SETUP_PATH/bin/gsectl" stop

    for i in 1 2 3 4 5 6 7 8 9 10; do
	    set -A pids $(ps -eo pid,comm | grep gse_agent |awk '{print$1}')
        #read -r -a pids <<< "$(pidof "$AGENT_SETUP_PATH"/bin/gse_agent)"
        if [[ ${#pids[@]} -eq 0 ]]; then
            log setup_agent SUCCESS 'old agent has been stopped successfully'
            break
        elif [[ $i -eq 10 ]]; then
            kill -9 "${pids[@]}"
        else
            sleep 1
        fi
    done
}

backup_config_file () {
    local file
    for file in "${BACKUP_CONFIG_FILES[@]}"; do
        local tmp_backup_file
        if [ -f "${AGENT_SETUP_PATH}/etc/${file}" ]; then
            tmp_backup_file=$(mktemp "${TMP_DIR}"/nodeman_${file}_config.XXXXXXX)
            log backup_config_file - "backup $file to $tmp_backup_file"
            cp -rf "${AGENT_SETUP_PATH}"/etc/"${file}" "${tmp_backup_file}"
            if [ $IS_SUPER == true ]; then
                chattr +i "${tmp_backup_file}"
            fi
        fi
    done
}

recovery_config_file () {
    for file in "${BACKUP_CONFIG_FILES[@]}"; do
        local latest_config_file tmp_config_file_abs_path
        time_filter_config_file=$(find "${TMP_DIR}" -ctime -1 -name "nodeman_${file}_config*")
        [ -z "${time_filter_config_file}" ] && return 0
        latest_config_file=$(find "${TMP_DIR}" -ctime -1 -name "nodeman_${file}_config*" | xargs ls -rth | tail -n 1)
        if [ $IS_SUPER == true ]; then
            chattr -i "${latest_config_file}"
        fi
        cp -rf "${latest_config_file}" "${AGENT_SETUP_PATH}"/etc/"${file}"
        rm -f "${latest_config_file}"
        log recovery_config_file - "recovery ${AGENT_SETUP_PATH}/etc/${file} from $latest_config_file"
    done
}

remove_agent () {
    log remove_agent - 'trying to stop old agent'
    stop_agent
    backup_config_file
    log remove_agent - "trying to remove old agent diretory(${AGENT_SETUP_PATH})"
    rm -rf "${AGENT_SETUP_PATH}"

    if [[ "$REMOVE" == "TRUE" ]]; then
        log remove_agent DONE "agent removed"
        exit 0
    else
        [[ -d $AGENT_SETUP_PATH ]] && return 0 || return 1
    fi
}


get_config () {
    local filename http_status
    set -A config agent.conf

    log get_config - "request $NODE_TYPE config file(s)"

    for filename in "${config[@]}"; do
        tmp_time=$(date +%Y%m%d_%H%M%S)
        tmp_date=$(date +%s)
        touch "/tmp/nm.reqbody."$tmp_time"."$tmp_date".json"
        touch "/tmp/nm.reqresp."$tmp_time"."$tmp_date".json"
        tmp_json_body="/tmp/nm.reqbody."$tmp_time"."$b_date".json"
        tmp_json_resp="/tmp/nm.reqresp."$tmp_time"."$b_date".json"
        cat > "$tmp_json_body" <<_OO_
{
    "bk_cloud_id": ${CLOUD_ID},
    "filename": "${filename}",
    "node_type": "${NODE_TYPE}",
    "inner_ip": "${LAN_ETH_IP}",
    "token": "${TOKEN}"
}
_OO_

        http_status=$(http_proxy=$HTTP_PROXY https_proxy=$HTTP_PROXY \
            curl -s -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/get_gse_config/ -o "$TMP_DIR/$filename" --silent -w "%{http_code}")
        rm -f "$tmp_json_body" "$tmp_json_resp"

        if [[ "$http_status" != "200" ]]; then
            fail get_config FAILED "request config $filename failed. request info:$CLOUD_ID,$LAN_ETH_IP,$NODE_TYPE,$filename,$TOKEN. http status:$http_status"
        fi
    done
}


get_aix_version () {
    oslevel |awk -F "." '{print$1}'
}

setup_agent () {
    log setup_agent START "setup agent. (extract, render config)"
    mkdir -p "$AGENT_SETUP_PATH"

    cd "$AGENT_SETUP_PATH/.."
    gunzip -dc "$TMP_DIR/$PKG_NAME" | tar xf -
    agent_name=gse_agent

    if [ -f agent/bin/"$agent_name" ]; then
        cp -f agent/bin/"$agent_name" agent/bin/gse_agent
    else
        fail "no agent/bin/$agent_name found"
    fi

    # update gsecmdline under /bin
    # cp -fp plugins/bin/gsecmdline /bin/
    # chmod 775 /bin/gsecmdline

    # setup config file
    get_config

    recovery_config_file
    set -A config agent.conf
    for f in "${config[@]}"; do
        if [[ -f $TMP_DIR/$f ]]; then
            cp -fp "$TMP_DIR/${f}" agent/etc/${f}
        else
            fail setup_agent FAILED "agent config file ${f}  lost. please check."
        fi
    done

    # create dir
    mkdir -p "$GSE_AGENT_RUN_DIR" "$GSE_AGENT_DATA_DIR" "$GSE_AGENT_LOG_DIR"

    start_agent

    log setup_agent DONE "agent setup succeded"
}

download_pkg () {
    local f http_status

    # 区分下载版本
    divide_version

    log download_pkg START "download gse agent package from $DOWNLOAD_URL/$PKG_NAME)."
    cd "$TMP_DIR" && rm -f "$PKG_NAME" "agent.conf.$LAN_ETH_IP"

    for f in $PKG_NAME; do
        http_status=$(http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY curl -O $DOWNLOAD_URL/$f \
                --silent -w "%{http_code}")
        # HTTP status 000需要进一步研究
        if [[ $http_status != "200" ]] && [[ "$http_status" != "000" ]]; then
            fail download_pkg FAILED "file $f download failed. (url:$DOWNLOAD_URL/$f, http_status:$http_status)"
        fi
    done

    log download_pkg DONE "gse_agent package download succeded"
    log report_cpu_arch DONE "${CPU_ARCH}"
}

check_deploy_result () {
    # 端口监听状态
    local ret=0

    get_pid
    #is_port_listen 48668         || { fail check_deploy_result FAILED "port 48668 is not listen"; ((ret++)); }
    is_port_listen "$BT_PORT_START" "$BT_PORT_END" || { fail check_deploy_result FAILED "bt port is not listen"; ((ret++)); }
    is_connected   "$IO_PORT"          || { fail check_deploy_result FAILED "agent(PID:$gse_Master) is not connect to gse server"; ((ret++)); }

    [ $ret -eq 0 ] && log check_deploy_result DONE "gse agent has bean deployed successfully"
}

validate_vars_string () {
    echo "$1" | grep -Pq '^[a-zA-Z_][a-zA-Z0-9_]*='
}

check_pkgtool () {
    local stderr_to
    stderr_to=$(touch /tmp/nm.chkpkg.`date +%s`)
    _yum=$(command -v yum 2>/dev/null)
    _apt=$(command -v apt 2>/dev/null)
    _dnf=$(command -v dnf 2>/dev/null)

    _curl=$(command -v curl 2>/dev/null)

    if [ -f "$_curl" ]; then
        return 0
    else
        log check_env - "trying to install curl by package management tool"
        if [ -f "$_yum" ]; then
            # yum 的报错可能有多行，此时错误信息的展示和上报需要单独处理
            yum -y -q install curl 2>"$stderr_to" || \
                fail check_env FAILED "install curl failed."
        elif [ -f "$_apt" ]; then
            apt-get -y install curl 2>"$stderr_to" || \
                fail check_env FAILED "install curl failed."
        elif [ -f "$_dnf" ]; then
            dnf -y -q install curl 2>"$stderr_to" || \
                fail check_env FAILED "install curl failed."
        else
            fail check_env FAILED "no curl command found and can not be installed by neither yum,dnf nor apt-get"
        fi

        log check_env - "curl has been installed"
    fi
}

check_disk_space () {
    if df -k "$TMP_DIR" | awk 'NR!=1 && $3 >= 300*1024 {x=1;}END{if (x== 1) {exit 0} else {exit 1}}'; then
        log check_env  - "check free disk space. done"
    else
        fail check_env FAILED "no enough space left on $TMP_DIR"
    fi
}

check_dir_permission () {
    mkdir -p "$TMP_DIR" || fail check-env FAILED "custom temprary dir '$TMP_DIR' create failed."
    datatemp=$(date +%s)
    if ! `touch "$TMP_DIR/nm.test.$datatemp" &>/dev/null` ; then
        rm "$TMP_DIR"/nm.test.*
        fail check_env FAILED "create temp files failed in $TMP_DIR"
    else
        log check_env  - "check temp dir write access: yes"
    fi
}

check_download_url () {
    local http_status f

    for f in $PKG_NAME; do
         log check_env - "checking resource($DOWNLOAD_URL/$f) url's validality"
         http_status=$(http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY curl -o /dev/null --silent -Iw '%{http_code}' "$DOWNLOAD_URL/$f")
         if [[ "$http_status" == "200" ]] || [[ "$http_status" == "000" ]]; then
             log check_env - "check resource($DOWNLOAD_URL/$f) url succeed"
         else
             fail check_env FAILED "check resource($DOWNLOAD_URL/$f) url failed, http_status:$http_status"
         fi
    done
}

check_target_clean () {
    if [[ -d $AGENT_SETUP_PATH/ ]]; then
        warn check_env - "directory $AGENT_SETUP_PATH is not clean. everything will be wippered unless -u was specified"
    fi
}

backup_for_upgrade () {
    local T
    cd "$AGENT_SETUP_PATH/.." || fail backup_config FAILED "change directory to $AGENT_SETUP_PATH/../ failed"

    if [ "$UPGRADE" == "TRUE" ]; then
        T=$(date +%F_%T)
        log backup_config - "backup configs for agents"
        cp -vfr agent/etc "etc.agent.${TASK_ID}.$T"
        log backup_config - "backup configs for plugins (if exists)"
        [ -d plugins/etc ] && cp -vrf plugins/etc "etc.plugins.${TASK_ID}.$T"
    fi
}

_help () {

    echo "${0%*/} -i CLOUD_ID -l URL -i CLOUD_ID -I LAN_IP [OPTIONS]"

    echo "  -I lan ip address on ethernet "
    echo "  -i CLOUD_ID"
    echo "  -l DOWNLOAD_URL"
    echo "  -s TASK_ID. [optional]"
    echo "  -c TOKEN. [optional]"
    echo "  -u upgrade action. [optional]"
    echo "  -r CALLBACK_URL, [optional]"
    echo "  -x HTTP_PROXY, [optional]"
    echo "  -p AGENT_SETUP_PATH, [optional]"
    echo "  -e BT_FILE_SERVER_IP, [optional]"
    echo "  -a DATA_SERVER_IP, [optional]"
    echo "  -k TASK_SERVER_IP, [optional]"
    echo "  -N UPSTREAM_TYPE, 'server' or 'proxy' [optional]"
    echo "  -T TEMP directory,[optional]"
    echo "  -v CUSTOM VARIABLES ASSIGNMENT LISTS. [optional]"
    echo "     valid variables:"
    echo "         GSE_AGENT_RUN_DIR"
    echo "         GSE_AGENT_DATA_DIR"
    echo "         GSE_AGENT_LOG_DIR"
    echo "  -o enable override OPTION DEFINED VARIABLES by -v. [optional]"
    echo "  -O IO_PORT"
    echo "  -E FILE_SVR_PORT"
    echo "  -A DATA_PORT"
    echo "  -V BTSVR_THRIFT_PORT"
    echo "  -B BT_PORT"
    echo "  -S BT_PORT_START"
    echo "  -Z BT_PORT_END"
    echo "  -K TRACKER_PORT"

    exit 0
}

check_env () {
    local node_type=${1:-$NODE_TYPE}

    log check_env START "checking prerequisite. NETWORK_POLICY,DISK_SPACE,PERMISSION,RESOURCE etc.[PID:$CURR_PID]"

    [ "$CLOUD_ID" != "0" ] && node_type=pagent
    validate_setup_path
    # check_polices_${node_type}_to_upstream
    # 目前Linux端口探测有三种方式

        # /proc 系统发送socket
        # telnet
        # python -c "import socket;client_socket=socket.socket();client_socket.connect(('$ip', $_port))"

   # 但是目前这几种方式在aix系统上都有问题, 所以暂时关闭探测逻辑
       # AIX 没有 /proc文件系统
       # AIX在telnet时出现长链接无断开，无返回
       # AIX系统本身无python解释器

    check_disk_space
    check_dir_permission
    check_pkgtool
    check_download_url
    check_target_clean

    log check_env DONE "checking prerequisite done, result: SUCCESS"
}

# DEFAULT SETTINGS
CLOUD_ID=0
TMP_DIR=/tmp
AGENT_SETUP_PATH="/usr/local/gse/${NODE_TYPE}"
CURR_PID=$$
UPGRADE=false
OVERIDE=false
REMOVE=false
CALLBACK_URL=
AGENT_PID=

# main program
while getopts I:i:l:s:uc:r:x:p:e:a:k:N:v:oT:RO:E:A:V:B:S:Z:K: arg; do
    case $arg in
        I) LAN_ETH_IP=$OPTARG ;;
        i) CLOUD_ID=$OPTARG ;;
        l) DOWNLOAD_URL=${OPTARG%/} ;;
        s) TASK_ID=$OPTARG ;;
        u) UPGRADE=TRUE ;;
        c) TOKEN=$OPTARG ;;
        r) CALLBACK_URL=$OPTARG ;;
        x) HTTP_PROXY=$OPTARG; HTTPS_PROXY=$OPTARG ;;
        p) AGENT_SETUP_PATH=$(echo "$OPTARG/$NODE_TYPE" | sed 's|//*|/|g') ;;
        e) BT_FILE_SERVER_IP=$(echo "$OPTARG" | awk -F , '{print$1}') ;;
        a) DATA_SERVER_IP=$(echo "$OPTARG" | awk -F , '{print$1}') ;;
        k) TASK_SERVER_IP=$(echo "$OPTARG" | awk -F , '{print$1}') ;;
        N) UPSTREAM_TYPE=$OPTARG ;;
        v) VARS_LIST="$OPTARG" ;;
        o) OVERIDE=TRUE ;;
        T) TMP_DIR=$OPTARG; mkdir -p "$TMP_DIR" ;;
        R) REMOVE=TRUE ;;
        O) IO_PORT=$OPTARG ;;
        E) FILE_SVR_PORT=$OPTARG ;;
        A) DATA_PORT=$OPTARG ;;
        V) BTSVR_THRIFT_PORT=$OPTARG ;;
        B) BT_PORT=$OPTARG ;;
        S) BT_PORT_START=$OPTARG ;;
        Z) BT_PORT_END=$OPTARG ;;
        K) TRACKER_PORT=$OPTARG ;;

        *)  _help ;;
    esac
done

IS_SUPER=true
if sudo -n true 2>/dev/null; then
    IS_SUPER=true
else
    IS_SUPER=false
fi

## 检查自定义环境变量
VARS_LIST=$(echo "$VARS_LIST" | sed 's/;/ /g')
for var_name in ${VARS_LIST}; do
    validate_vars_string "$var_name" || fail "$var_name is not a valid name"

    case ${var_name%=*} in
        CLOUD_ID | DOWNLOAD_URL | TASK_ID | CALLBACK_URL | HOST_LIST_FILE | NODEMAN_PROXY | AGENT_SETUP_PATH)
            [ "$OVERIDE" == "TRUE" ] || continue ;;
        VARS_LIST) continue ;;
    esac

    eval "$var_name"
done

LOG_FILE=/tmp/nm.${0##*/}.$TASK_ID

log check_env - "$@"
# 整体安装流程:
#pre_view
for step in check_env \
            download_pkg \
            remove_crontab \
            remove_agent \
            remove_proxy_if_exists \
            setup_agent \
            setup_startup_scripts \
            setup_crontab \
            check_deploy_result; do
    $step
done
