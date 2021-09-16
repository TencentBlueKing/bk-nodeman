#!/bin/bash
# vim:ft=sh expandtab sts=4 ts=4 sw=4 nu
# gse agent安装脚本, 仅在节点管理2.0中使用

# DEFAULT DEFINITION
NODE_TYPE=agent

GSE_AGENT_RUN_DIR=/var/run/gse
GSE_AGENT_DATA_DIR=/var/lib/gse
GSE_AGENT_LOG_DIR=/var/log/gse

OS_INFO=""
OS_TYPE=""
RC_LOCAL_FILE=/etc/rc.d/rc.local

# 收到如下信号或者exit退出时，执行清理逻辑
#trap quit 1 2 3 4 5 6 7 8 10 11 12 13 14 15
trap 'cleanup' HUP INT QUIT ABRT SEGV PIPE ALRM TERM EXIT
trap 'report_err $LINENO; exit 1; ' ERR

log ()  { local L=INFO D;  D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; bulk_report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" ; return 0; }
warn () { local L=WARN D;  D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; bulk_report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" ; return 0; }
err ()  { local L=ERROR D; D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; bulk_report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" ; return 1; }
fail () { local L=ERROR D; D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; bulk_report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" URG; exit 1; }

get_cpu_arch () {
    local cmd=$1
    CPU_ARCH=$($cmd)
    CPU_ARCH=$(echo ${CPU_ARCH} | tr 'A-Z' 'a-z')
    if [[ "${CPU_ARCH}" =~ "x86_64" ]]; then
        return 0
    elif [[ "${CPU_ARCH}" =~ "x86" || "${CPU_ARCH}" =~ ^i[3456]86 ]]; then
        CPU_ARCH="x86"
        return 0
    elif [[ "${CPU_ARCH}" =~ "aarch" ]]; then
        return 0
    else
        return 1
    fi
}

get_cpu_arch "uname -p" || get_cpu_arch "uname -m" || fail get_cpu_arch "Failed to get CPU arch, please contact the developer."

PKG_NAME=gse_client-linux-${CPU_ARCH}.tgz

get_os_info () {
    if [ -f "/proc/version" ]; then
        OS_INFO="$OS_INFO $(cat /proc/version)"
    fi
    if [ -f "/etc/issue" ]; then
        OS_INFO="$OS_INFO $(cat /etc/issue)"
    fi
    OS_INFO="$OS_INFO $(uname -a)"
    OS_INFO=$(echo ${OS_INFO} | tr 'A-Z' 'a-z')
}

get_os_type () {
    get_os_info
    OS_INFO=$(echo ${OS_INFO} | tr 'A-Z' 'a-z')
    if [[ "${OS_INFO}" =~ "ubuntu" ]]; then
        OS_TYPE="ubuntu"
        RC_LOCAL_FILE="/etc/rc.local"
    elif [[ "${OS_INFO}" =~ "centos" ]]; then
        OS_TYPE="centos"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "${OS_INFO}" =~ "coreos" ]]; then
        OS_TYPE="coreos"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "${OS_INFO}" =~ "freebsd" ]]; then
        OS_TYPE="freebsd"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "${OS_INFO}" =~ "debian" ]]; then
        OS_TYPE="debian"
        RC_LOCAL_FILE="/etc/rc.local"
    elif [[ "${OS_INFO}" =~ "suse" ]]; then
        OS_TYPE="suse"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "${OS_INFO,,}" =~ "hat" ]]; then
        OS_TYPE="redhat"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    fi
}

check_rc_file () {
    get_os_type
    if [ -f $RC_LOCAL_FILE ]; then
        return 0
    elif [ -f "/etc/rc.d/rc.local" ]; then
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    else
        RC_LOCAL_FILE="/etc/rc.local"
    fi
}

# 清理逻辑：保留本次的LOG_FILE,下次运行时会删除历史的LOG_FILE。
# 保留安装脚本本身
cleanup () {
    bulk_report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" URG # 上报所有剩余的日志

    if ! [[ $DEBUG = "true" ]]; then
        local GLOBIGNORE="$LOG_FILE*"
        rm -vf "$TMP_DIR"/nm.*
    fi

    exit 0
}

# 打印错误行数信息
report_err () {
    awk -v LN="$1" -v L="ERROR" -v D="$(date +%F\ %T)" \
        'NR>LN-3 && NR<LN+3 { printf "%s %s cmd-return-err %-5d%3s%s\n", D, L, NR, (NR==LN?">>>":""), $0 }' $0 
}

validate_setup_path () {
    local invalid_path_prefix=(
        /tmp
        /var
        /etc
        /bin
        /lib
        /lib64
        /boot
        /mnt
        /proc
        /dev
        /run
        /sys
        /sbin
        /root
        /home
    )

    local invalid_path=(
        /usr
        /usr/bin
        /usr/sbin
        /usr/local/lib
        /usr/include
        /usr/lib
        /usr/lib64
        /usr/libexec
    )

    local p1="${AGENT_SETUP_PATH%/$NODE_TYPE*}"
    local p2="${p1%/gse*}"
    local p

    if [[ "$p1" == "${AGENT_SETUP_PATH}" ]] || [[ "$p2" == "$AGENT_SETUP_PATH" ]]; then
        fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
    fi

    for p in "${invalid_path[@]}"; do
        if [[ "${p2}" == "$p" ]]; then
            fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
        fi
    done

    for p in "${invalid_path_prefix[@]}"; do
        if [[ "${p2//$p}" != "$p2" ]]; then
            fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
        fi
    done
}

is_port_listen () {
    local i port

    for i in {0..15}; do
        sleep 1
        for port in "$@"; do
            lsof -iTCP:"$port" -sTCP:LISTEN -a -i -P -n -p "$AGENT_PID" && return 0
        done
    done

    return 1
}

# 判断某个pid是否监听指定的端口列表
# 利用linux内核/proc/<pid>/net/tcp文件中第四列0A表示LISTEN
# 第二列16进制表达的ip和port
is_port_listen_by_pid () {
    local pid regex
    pid=$1
    shift 1

    for i in {0..10}; do
        sleep 1
        for port in "$@"; do
            stat -L -c %i /proc/"$pid"/fd/* 2>/dev/null \
                | grep -qwFf - \
                    <( awk -v p="$port" 'BEGIN{ check=sprintf(":%04X0A$", p)} $2$4 ~ check {print $10}' /proc/net/tcp) \
                    && return 0
        done
    done
    return 1
}

is_port_connected_by_pid () {
    local pid port regex
    pid=$1 port=$2

    for i in {0..10}; do
        sleep 1
        stat -L -c %i /proc/"$pid"/fd/* 2>/dev/null \
            | grep -qwFf - \
                <( awk -v p="$port" 'BEGIN{ check=sprintf(":%04X01$", p)} $3$4 ~ check {print $10}' /proc/net/tcp) \
                && return 0
    done
    return 1
}

is_connected () {
    local i port=$1

    for i in {0..15}; do
        sleep 1
        lsof -iTCP:"$port" -sTCP:ESTABLISHED -a -i -P -n -p "$AGENT_PID" && return 0
    done

    return 1
}

is_gsecmdline_ok () {
   /bin/gsecmdline -d 1430 -s test
}

# 用法：通过ps的comm字段和二进制的绝对路径来精确获取pid
get_pid_by_comm_path () {
    local comm=$1 path=$2
    local _pids pids
    local pid
    read -r -a _pids <<< "$(ps --no-header -C "$comm" -o pid | xargs)"

    # 传入了绝对路径，则进行基于二进制路径的筛选
    if [[ -e "$path" ]]; then
        for pid in "${_pids[@]}"; do
            if [[ "$(readlink -f "$path")" = "$(readlink -f /proc/"$pid"/exe)" ]]; then
                if ! grep -nEq '^\ +$' <<< "$pid"; then
                    pids+=("$pid")
                fi
            fi
        done
    else
        pids=("${_pids[@]}")
    fi

    echo ${pids[@]}
}

is_process_ok () {
    local proc=${1:-agent}
    local gse_master gse_workers
    local gse_master_pids
    gse_master_pids="$( get_pid_by_comm_path gseMaster "$AGENT_SETUP_PATH/bin/gse_${proc}" | xargs)"
    read -r -a gse_master <<< "$gse_master_pids"
    read -r -a gse_workers <<< "$( get_pid_by_comm_path "${proc}Worker" "$AGENT_SETUP_PATH/bin/gse_${proc}" | xargs)"
    if [ "${#gse_master[@]}" -eq 0 ]; then
        fail setup_agent FAILED "process check: no gseMaster found. gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    if [ "${#gse_master[@]}" -gt 1 ]; then
        fail setup_agent FAILED "process check: ${#gse_master[@]} gseMaster found. pid($gse_master_pids) gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    # worker 进程在某些任务情况下可能不只一个，只要都是一个爹，多个worker也是正常，不为0即可
    if [ "${#gse_workers[@]}" -eq 0 ]; then
        fail setup_agent FAILED "process check: ${proc}Worker not found (node type:$NODE_TYPE)"
    fi
}

is_target_reachable () {
    local ip="$1"
    local target_port="$2"
    local ports=()
    local _port err timeout_exist

    if [[ $target_port =~ [0-9]+-[0-9]+ ]]; then
        ports=( $(seq ${target_port//-/ }) )
    else
        ports=( "$target_port" )
    fi

    # 判断timeout命令是否存在
    hash timeout 2>/dev/null
    case $? in
        0) timeout_exist=0 ;;
        1) timeout_exist=1 ;;
    esac

    for _port in "${ports[@]}"; do
        if [ "$timeout_exist" -eq 0 ]; then
            timeout 5 bash -c ">/dev/tcp/$ip/$_port"
        else
            bash -c ">/dev/tcp/$ip/$_port"
        fi
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

    # 非直连Agent的上级节点是所属云区域的proxy
    for ip in "${TASK_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $IO_PORT of $ip($UPSTREAM_TYPE)"
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

check_polices_proxy_to_upstream () {
    #local proxy_to_server_policies=(gse_task:48668 gse_data:58625 gse_btsvr:58930 gse_btsvr:10020-10030 gse_ops:58725)
    #local proxy_listen_ports=(gse_agent:48668 gse_transit:58625 gse_btsvr:58930 gse_btsvr:58925 gse_btsvr:10020-10030 gse_opts:58725)
    local ip

    # GSE Proxy 的上级节点可能是 GSE Server(不同的接入点), 也可能是一级Proxy节点
    for ip in "${TASK_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $IO_PORT of $ip(${UPSTREAM_TYPE:-GSE_TASK_SERVER})"
        is_target_reachable "$ip" "$IO_PORT"
    done

    for ip in "${DATA_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $DATA_PORT of $ip(${UPSTREAM_TYPE:-GSE_DATA_SERVER})"
        is_target_reachable "$ip" "$DATA_PORT"
    done

    for ip in "${BT_FILE_SERVER_IP[@]}"; do
        log check_env - "check if it is reachable to port $BTSVR_THRIFT_PORT of $ip(${UPSTREAM_TYPE:-GSE_BTFILE_SERVER})"
        is_target_reachable "$ip" "$BTSVR_THRIFT_PORT"
        is_target_reachable "$ip" "$BT_PORT"
    done
}

pre_view () {
   log PREVIEW - "---- precheck current deployed agent info ----"

   if [[ -f $AGENT_SETUP_PATH/etc/agent.conf ]]; then
       log PREVIEW - "normalized agent:"
       log PREVIEW - "   setup path: $(readlink -f "${AGENT_SETUP_PATH}"/bin/gse_agent)"
       log PREVIEW - "   process:"
           lsof -a -d txt -c agentWorker -c gseMaster -a -n "$AGENT_SETUP_PATH"/bin/gse_agent
       log PREVIEW - "   gsecmdline: $(is_gsecmdline_ok && echo OK || echo NO)"
    fi
}

remove_crontab () {
    local tmpcron
    tmpcron=$(mktemp "$TMP_DIR"/cron.XXXXXXX)

    crontab -l | grep -v "$AGENT_SETUP_PATH/bin/gsectl"  >"$tmpcron"
    crontab "$tmpcron" && rm -f "$tmpcron"

    # 下面这段代码是为了确保修改的crontab能立即生效
    if pgrep -x crond &>/dev/null; then
        pkill -HUP -x crond 
    fi
}

setup_startup_scripts () {
    check_rc_file
    local rcfile=$RC_LOCAL_FILE

    if [ $OS_TYPE == "ubuntu" ]; then
        sed -i "\|\#\!/bin/bash|d" $rcfile
        sed -i "1i \#\!/bin/bash" $rcfile
    fi
    chmod +x $rcfile
    # 先删后加，避免重复
    sed -i "\|${AGENT_SETUP_PATH}/bin/gsectl|d" $rcfile

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

    for p in agent transit btsvr; do
        for i in {0..10}; do
            read -r -a pids <<< "$(pidof "$path"/bin/gse_${p})"
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

    for i in {1..10}; do
        read -r -a pids <<< "$(pidof "$AGENT_SETUP_PATH"/bin/gse_agent)"
        if [[ ${#pids[@]} -eq 0 ]]; then
            log remove_agent SUCCESS 'old agent has been stopped successfully'
            break
        elif [[ $i -eq 10 ]]; then
            kill -9 "${pids[@]}"
        else
            sleep 1
        fi
    done
}

remove_agent () {
    log remove_agent - 'trying to stop old agent'
    stop_agent

    log remove_agent - "trying to remove old agent directory(${AGENT_SETUP_PATH})"
    chattr -i -R "${AGENT_SETUP_PATH}" > /dev/null 2>&1
    rm -rf "${AGENT_SETUP_PATH}"

    if [[ "$REMOVE" == "TRUE" ]]; then
        log remove_agent DONE "agent removed"
        exit 0
    fi
}

get_config () {
    local filename http_status
    local config=(agent.conf)

    log get_config - "request $NODE_TYPE config file(s)"

    for filename in "${config[@]}"; do
        tmp_json_body=$(mktemp "$TMP_DIR"/nm.reqbody."$(date +%Y%m%d_%H%M%S)".XXXXXX.json)
        tmp_json_resp=$(mktemp "$TMP_DIR"/nm.reqresp."$(date +%Y%m%d_%H%M%S)".XXXXXX.json)
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

setup_agent () {
    log setup_agent START "setup agent. (extract, render config)"
    mkdir -p "$AGENT_SETUP_PATH"

    cd "$AGENT_SETUP_PATH/.." && tar xf "$TMP_DIR/$PKG_NAME"

    # update gsecmdline under /bin
    cp -fp plugins/bin/gsecmdline /bin/
    # 注意这里 /bin/ 可能是软链
    cp -fp plugins/etc/gsecmdline.conf /bin/../etc/
    chmod 775 /bin/gsecmdline

    # setup config file
    get_config

    local config=(agent.conf)
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

    log setup_agent DONE "gse agent is setup successfully."
}

start_basic_gse_plugin () {
    log start_plugin START "start gse plugin: basereport, processbeat"
    cd "$AGENT_SETUP_PATH/../plugins/bin" || fail start_plugin FAILED "change directory to $AGENT_SETUP_PATH/../plugins/bin failed"

    if [[ -x ./basereport ]]; then
        ./stop.sh basereport
        ./start.sh basereport || fail start_plugin FAILED "basereport start failed."
    fi
    if [[ -x ./processbeat ]]; then
        ./stop.sh processbeat
        ./start.sh processbeat || fail start_plugin FAILED "processbeat start failed."
    fi

    log start_plugin DONE "gse plugin 'basereport,processbeat start done."
}

download_pkg () {
    local f http_status path
    local tmp_stdout tmp_stderr curl_pid

    log download_pkg START "download gse agent package from $DOWNLOAD_URL/$PKG_NAME)."
    cd "$TMP_DIR" && rm -f "$PKG_NAME" "agent.conf.$LAN_ETH_IP"

    for f in $PKG_NAME; do
        tmp_stdout=$(mktemp "${TMP_DIR}"/nm.curl.stdout_XXXXXXXX)
        tmp_stderr=$(mktemp "${TMP_DIR}"/nm.curl.stderr_XXXXXXXX)
        curl --connect-timeout 5 -o "$TMP_DIR/$f" \
                --progress-bar -w "%{http_code}" "$DOWNLOAD_URL/$f" >"$tmp_stdout" 2>"$tmp_stderr" &
        curl_pid=$!
        # 如果curl结束，那么http_code一定会写入到stdout文件
        until [[ -n $http_status ]]; do
            read -r http_status < "$tmp_stdout"
            # 为了上报curl的进度
            log download_pkg DOWNLOADING "$(awk 'BEGIN { RS="\r"; } END { print }' < "$tmp_stderr")"
            sleep 1
        done
        rm -f "${tmp_stdout}" "${tmp_stderr}"
        wait "$curl_pid"

        # HTTP status 000需要进一步研究
        if [[ $http_status != "200" ]] && [[ "$http_status" != "000" ]]; then
            fail download_pkg FAILED "file $f download failed. (url:$DOWNLOAD_URL/$f, http_status:$http_status)"
        fi
    done

    log download_pkg DONE "gse_agent package download succeeded"
    log report_cpu_arch DONE "${CPU_ARCH}"
}

check_deploy_result () {
    # 端口监听状态
    local ret=0

    AGENT_PID=$( get_pid_by_comm_path agentWorker "$AGENT_SETUP_PATH/bin/gse_agent" )
    is_port_listen_by_pid "$AGENT_PID" $(seq "$BT_PORT_START" "$BT_PORT_END") || { fail check_deploy_result FAILED "agent(PID:$AGENT_PID) bt port is not listen"; ((ret++)); }
    is_port_connected_by_pid "$AGENT_PID"  "$IO_PORT"      || { fail check_deploy_result FAILED "agent(PID:$AGENT_PID) is not connect to gse server"; ((ret++)); }

    [ $ret -eq 0 ] && log check_deploy_result DONE "gse agent has been deployed successfully"
}

# 日志行转为json格式函数
log_to_json () {
    local date _time log_level step status message
    read -r date _time log_level step status message <<<"$@"

    printf '{"timestamp": "%s", "level": "%s", "step":"%s", "log":"%s","status":"%s"}' \
        "$(date +%s -d "$date $_time")" \
        "$log_level" "$step" "$message" "$status"
}

# 读入LOG_FILE的日志然后批量上报
# 用法：bulk_report_step_status <log_file> <bulk_size:3> <is_urg>
bulk_report_step_status () {
    local log_file=$1
    local bulk_size=${2:-3} # 默认设置为累积三条报一次
    local is_urg=${3:-""}   # 设置URG后立即上报
    local log_total_line diff
    local bulk_log log=() line json_log
    local tmp_json_body tmp_json_resp

    # 未设置上报API时，直接忽略
    [[ -z "$CALLBACK_URL" ]] && return 0
    log_total_line=$(wc -l <"$log_file")
    diff=$(( log_total_line - LOG_RPT_CNT ))

    if (( diff >= bulk_size )) || [[ $is_urg = "URG" ]]; then
        ((LOG_RPT_CNT++))   #always report from next line
        bulk_log=$(sed -n "${LOG_RPT_CNT},${log_total_line}p" "$log_file")
        # 如果刚好 log_total_line能整除 bulk_size时，最后EXIT的URG调用会触发一个空行
        # 判断如果是空字符串则不上报
        if [[ -z "$bulk_log" ]]; then
            return 0
        fi
    else
        return 0
    fi
    LOG_RPT_CNT=$log_total_line

    # 构建log数组
    while read -r line; do
        log+=( "$(log_to_json "$line")" )
    done <<< "$bulk_log"
    # 生成log json array
    json_log=$(printf "%s," "${log[@]}")
    json_log=${json_log%,}

    tmp_json_body=$(mktemp "$TMP_DIR"/nm.reqbody."$(date +%Y%m%d_%H%M%S)".XXXXXX.json)
    tmp_json_resp=$(mktemp "$TMP_DIR"/nm.reqresp."$(date +%Y%m%d_%H%M%S)".XXXXXX.json)

    cat > "$tmp_json_body" <<_OO_
{
    "task_id": "$TASK_ID",
    "token": "$TOKEN",
    "logs": [ $json_log ]
}
_OO_

    http_proxy=$HTTP_PROXY https_proxy=$HTTP_PROXY \
        curl -s -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/report_log/ -o "$tmp_json_resp"
    rm -f "$tmp_json_body" "$tmp_json_resp"
}

report_step_status () {
    local date _time log_level step status message
    local tmp_json_body tmp_json_resp

    # 未设置上报API时，直接忽略
    [ -z "$CALLBACK_URL" ] && return 0

    read -r date _time log_level step status message <<<"$@"

    tmp_json_body=$(mktemp "$TMP_DIR"/nm.reqbody."$(date +%Y%m%d_%H%M%S)".XXXXXX.json)
    tmp_json_resp=$(mktemp "$TMP_DIR"/nm.reqresp."$(date +%Y%m%d_%H%M%S)".XXXXXX.json)


    cat > "$tmp_json_body" <<_OO_
{
    "task_id": "$TASK_ID",
    "token": "$TOKEN",
    "logs": [
        {
            "timestamp": "$(date +%s -d "$date $_time")",
            "level": "$log_level",
            "step": "$step",
            "log": "$message",
            "status": "$status"
        }
    ]
}
_OO_

    http_proxy=$HTTP_PROXY https_proxy=$HTTP_PROXY \
        curl -s -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/report_log/ -o "$tmp_json_resp"
    rm -f "$tmp_json_body" "$tmp_json_resp"
}

validate_vars_string () {
    echo "$1" | grep -Pq '^[a-zA-Z_][a-zA-Z0-9]+='
}

check_pkgtool () {
    _yum=$(command -v yum)
    _apt=$(command -v apt)
    _dnf=$(command -v dnf)

    _curl=$(command -v curl)

    if [ -f "$_curl" ]; then
        return 0
    else
        log check_env - "trying to install curl by package management tool"
        if [ -f "$_yum" ]; then
            # yum 的报错可能有多行，此时错误信息的展示和上报需要单独处理
            yum -y -q install curl || \
                fail check_env FAILED "install curl failed."
        elif [ -f "$_apt" ]; then
            apt-get -y install curl || \
                fail check_env FAILED "install curl failed."
        elif [ -f "$_dnf" ]; then
            dnf -y -q install curl || \
                fail check_env FAILED "install curl failed."
        else
            fail check_env FAILED "no curl command found and can not be installed by neither yum,dnf nor apt-get"
        fi

        log check_env - "curl has been installed"
    fi
}

check_disk_space () {
    local dir=$1
    if df -x tmpfs -x devtmpfs --output=avail -k "$TMP_DIR" | awk 'NR==2 { if ($1 < 300 * 1024 ) { exit 1 } else {exit 0} }'; then
        log check_env  - "check free disk space. done"
    else
        fail check_env FAILED "no enough space left on $dir"
    fi
}

check_dir_permission () {
    mkdir -p "$TMP_DIR" || fail check-env FAILED "custom temprary dir '$TMP_DIR' create failed."

    if ! mktemp "$TMP_DIR/nm.test.XXXXXXXX"; then
        rm "$TMP_DIR"/nm.test.????????
        fail check_env FAILED "create temp files failed in $TMP_DIR"
    else
        log check_env  - "check temp dir write access: yes"
    fi
}

check_download_url () {
    local http_status f

    for f in $PKG_NAME; do
         log check_env - "checking resource($DOWNLOAD_URL/$f) url's validality"
         http_status=$(curl -o /dev/null --silent -Iw '%{http_code}' "$DOWNLOAD_URL/$f")
         if [[ "$http_status" == "200" ]] || [[ "$http_status" == "000" ]]; then
             log check_env - "check resource($DOWNLOAD_URL/$f) url succeed"
         else
             fail check_env FAILED "check resource($DOWNLOAD_URL/$f) url failed, http_status:$http_status"
         fi
    done
}

check_target_clean () {
    if [[ -d $AGENT_SETUP_PATH/ ]]; then
        warn check_env - "directory $AGENT_SETUP_PATH is not clean. everything will be wiped unless -u was specified"
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

    echo "${0%*/} -i CLOUD_ID -l URL -I LAN_IP [OPTIONS]"

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
    echo "  -T TEMP directory, [optional]"
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
    check_polices_${node_type}_to_upstream
    check_disk_space "$TMP_DIR"
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
DEBUG=

# 已上报的日志行数
LOG_RPT_CNT=0
BULK_LOG_SIZE=3

# main program
while getopts I:i:l:s:uc:r:x:p:e:a:k:N:v:oT:RDO:E:A:V:B:S:Z:K: arg; do
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
        e) read -r -a BT_FILE_SERVER_IP <<< "${OPTARG//,/ }" ;;
        a) read -r -a DATA_SERVER_IP <<< "${OPTARG//,/ }" ;;
        k) read -r -a TASK_SERVER_IP <<< "${OPTARG//,/ }" ;;
        N) UPSTREAM_TYPE=$OPTARG ;;
        v) VARS_LIST="$OPTARG" ;;
        o) OVERIDE=TRUE ;;
        T) TMP_DIR=$OPTARG; mkdir -p "$TMP_DIR" ;;
        R) REMOVE=TRUE ;;
        D) DEBUG=TRUE ;;
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

## 检查自定义环境变量
for var_name in ${VARS_LIST//;/ /}; do
    validate_vars_string "$var_name" || fail "$var_name is not a valid name"

    case ${var_name%=*} in
        CLOUD_ID | DOWNLOAD_URL | TASK_ID | CALLBACK_URL | HOST_LIST_FILE | NODEMAN_PROXY | AGENT_SETUP_PATH)
            [ "$OVERIDE" == "TRUE" ] || continue ;;
        VARS_LIST) continue ;;
    esac

    eval "$var_name"
done

LOG_FILE="$TMP_DIR"/nm.${0##*/}.$TASK_ID
DEBUG_LOG_FILE=${TMP_DIR}/nm.${0##*/}.${TASK_ID}.debug

# redirect STDOUT & STDERR to DEBUG
exec &> >(tee "$DEBUG_LOG_FILE")

log check_env - "Args are: $*"
for step in check_env \
            download_pkg \
            remove_crontab \
            remove_agent \
            remove_proxy_if_exists \
            setup_agent \
            start_basic_gse_plugin \
            setup_startup_scripts \
            check_deploy_result; do
    $step
done
