#!/bin/bash
# vim:ft=sh expandtab sts=4 ts=4 sw=4 nu
# gse proxy 2.0 安装脚本, 仅在节点管理2.0中使用

get_cpu_arch () {
    local cmd=$1
    CPU_ARCH=$($cmd)
    CPU_ARCH=$(echo ${CPU_ARCH} | tr 'A-Z' 'a-z')
    if [[ "${CPU_ARCH}" =~ "x86_64" ]]; then
        return 0
    elif [[ "${CPU_ARCH}" =~ "x86" || "${CPU_ARCH}" =~ ^i[3456]86 ]]; then
        return 1
    elif [[ "${CPU_ARCH}" =~ "aarch" ]]; then
        return 0
    else
        return 1
    fi
}
get_cpu_arch "uname -p" || get_cpu_arch "uname -m" || fail get_cpu_arch "Failed to get CPU arch or unsupported CPU arch, please contact the developer."

NODE_TYPE=proxy
PROC_LIST=(agent data file)
GSE_AGENT_RUN_DIR=/var/run/gse
GSE_AGENT_DATA_DIR=/var/lib/gse
GSE_AGENT_LOG_DIR=/var/log/gse
PROXY_CONFIGS=(gse_agent.conf gse_data_proxy.conf gse_file_proxy.conf)
GSE_AGENT_CONFIG="gse_agent.conf"
PROXY_CLEAN_UP_DIRS=("bin")


PKG_NAME=""
OS_INFO=""
OS_TYPE=""
RC_LOCAL_FILE=/etc/rc.d/rc.local

# 收到如下信号或者exit退出时，执行清理逻辑
#trap quit 1 2 3 4 5 6 7 8 10 11 12 13 14 15
trap cleanup HUP INT QUIT ABRT SEGV PIPE ALRM TERM EXIT

log ()  { local L=INFO D;  D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; return 0; }
warn () { local L=WARN D;  D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; return 0; }
err ()  { local L=ERROR D; D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; return 1; }
fail () { local L=ERROR D; D="$(date +%F\ %T)"; echo "$D $L $*" | tee -a "$LOG_FILE"; report_step_status "$D" "$L" "$@"; exit 1; }

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
    local GLOBIGNORE="$LOG_FILE*"
    rm -vf "$TMP_DIR"/nm.*

    exit 0
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
            lsof -iTCP:"$port" -sTCP:LISTEN -a -i -P -n -p "$AGENT_PID" 2>/dev/null && return 0
        done
    done

    return 1
}

proc_connect_check () {
    local pid="$1" port="$2"
    if stat -L -c %i /proc/"$pid"/fd/* 2>/dev/null  | grep -qwFf - <( awk -v p="$port" 'BEGIN{ check=sprintf(":%04X0A$", p)} $2$4 ~ check {print $10}' /proc/net/tcp); then
        return 0
    elif stat -L -c %i /proc/"$pid"/fd/* 2>/dev/null | grep -qwFf - <( awk -v p="$port" 'BEGIN{ check=sprintf(":%04X0A$", p)} $2$4 ~ check {print $10}' /proc/net/tcp6); then
        return 0
    else
        return 1
    fi

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
            proc_connect_check $pid $port && return 0
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
                <( awk -v p="$port" 'BEGIN{ check=sprintf(":%04X01$", p)} $3$4 ~ check {print $10}' /proc/net/tcp*) \
                && return 0
    done
    return 1
}

is_connected () {
    local i port=$1

    for i in {0..15}; do
        sleep 1
        lsof -iTCP:"$port" -sTCP:ESTABLISHED -a -i -P -n -p "$AGENT_PID" 2>/dev/null && return 0
    done

    return 1
}

# 用法：通过ps的comm字段和二进制的绝对路径来精确获取pid
get_pid_by_comm_path () {
    local comm=$1 path=$2 worker=$3
    local _pids pids
    local pid
    if [[ "${worker}" == "WORKER" ]]; then
        read -r -a _pids <<< "$(ps --no-header -C $comm -o '%P|%p|%a' | awk -v proc="${comm}" -F'|' '$1 != 1 && $3 ~ proc' | awk -F'|' '{print $2}' | xargs)"
    elif [[ "${worker}" == "MASTER" ]]; then
        read -r -a _pids <<< "$(ps --no-header -C $comm -o '%P|%p|%a' | awk -v proc="${comm}" -F'|' '$1 == 1 && $3 ~ proc' | awk -F'|' '{print $2}' | xargs)"
    else
        read -r -a _pids <<< "$(ps --no-header -C "$comm" -o pid | xargs)"
    fi

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
    local gse_master_pid gse_worker_pids gse_proc_pids
    gse_proc_pids="$(get_pid_by_comm_path gse_"${proc}" "$AGENT_SETUP_PATH/bin/gse_${proc}" | xargs)"
    gse_master_pid=$(get_pid_by_comm_path gse_"${proc}" "$AGENT_SETUP_PATH/bin/gse_${proc}" MASTER | xargs)

    read -r -a gse_master <<< "$gse_master_pids"
    read -r -a gse_pids <<< "$gse_proc_pids"

    proc_pid_file="${AGENT_SETUP_PATH}/bin/run/${proc}.pid"

    if [[ ${#gse_master} -gt 1 && -f ${proc_pid_file} ]]; then
        gse_master_pid=$(cat "${proc_pid_file}")
    fi

    gse_worker_pids=$(pgrep -P "$gse_master_pid")

    read -r -a gse_worker <<< "$gse_worker_pids"

    if [ "${#gse_pids[@]}" -eq 0 ]; then
        fail setup_agent FAILED "process check: no gse_agent found. gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    if [ "${#gse_master[@]}" -gt 1 ]; then
        fail setup_agent FAILED "process check: ${#gse_master[@]} gse_${proc} Master found. pid($gse_master_pids) gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    # worker 进程在某些任务情况下可能不只一个，只要都是一个爹，多个worker也是正常，不为0即可
    if [ "${#gse_worker[@]}" -eq 0 ]; then
        fail setup_agent FAILED "process check: gse_${proc} Worker not found (node type:$NODE_TYPE)"
    fi
}

pre_view () {
   log PREVIEW - "---- precheck current deployed agent info ----"

   if [[ -f $AGENT_SETUP_PATH/etc/agent.conf ]]; then
       log PREVIEW - "normalized agent:"
       log PREVIEW - "   setup path: $(readlink -f "${AGENT_SETUP_PATH}"/bin/gse_agent)"
       log PREVIEW - "   process:"
           lsof -a -d txt -c agentWorker -c gseMaster -a -n "$AGENT_SETUP_PATH"/bin/gse_agent
    fi
}

report_mkdir () {
    local dirs="$@"
    for dir in ${dirs[@]}; do
        local result
        if [[ -d "${dir}" ]]; then
            continue
        else
            result="$(mkdir -p ${dir} 2>&1)"
            if [ $? -ne 0 ]; then
                if [[ -f "${dir}" ]]; then
                    fail check_env FAILED "create directory $dir failed. error: ${dir} exists and is a normal file"
                else
                    fail check_env FAILED "create directory $dir failed. error: ${result}"
                fi
            fi
        fi
    done
}

remove_crontab () {
    local tmpcron
    tmpcron=$(mktemp "$TMP_DIR"/cron.XXXXXXX)

    crontab -l | grep -v "bin/gsectl"  >"$tmpcron"
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

start_proxy () {
    local i p

    "$AGENT_SETUP_PATH"/bin/gsectl start || fail setup_proxy FAILED "start gse proxy failed"

    sleep 3
    for p in "${PROC_LIST[@]}"; do
        is_process_ok $p || fail setup_proxy FAILED "start gse proxy failed, process -> [gse_$p] is not ready!"
        sleep 1
    done
}

registe_agent_with_excepte () {
    local SLEEP_TIME=1 RETRY_COUNT=0

    for i in {0..2}; do
        local registe_result registe_code
        if [ -f "${GSE_AGENT_CONFIG_PATH}" ]; then
            registe_result=$($AGENT_SETUP_PATH/bin/gse_agent -f "${GSE_AGENT_CONFIG_PATH}" --register 2>&1)
        else
            registe_result=$($AGENT_SETUP_PATH/bin/gse_agent --register 2>&1)
        fi
        registe_code=$?
        if [[ "${registe_code}" -eq 0 ]] && [[ ! "${registe_result}" =~ "overwrite" ]]; then
            log report_agent_id DONE "$registe_result"
            break
        else
            sleep "${SLEEP_TIME}"
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [[ "${RETRY_COUNT}" -ge 3 ]]; then
                fail register_agent_id FAILED "register agent id failed, error: ${registe_result}"
            fi
        fi
    done
}

register_agent_id () {
    if [ ! -f "$AGENT_SETUP_PATH/bin/gse_agent" ]; then
        fail register_agent_id FAILED "gse_agent file not exists in $AGENT_SETUP_PATH/bin"
    fi

    if [[ "${UNREGISTER_AGENT_ID}" == "TRUE" ]]; then
        log register_agent_id - "trying to unregister agent id"
        unregister_agent_id SKIP
    fi

    log register_agent_id  - "trying to register agent id"
    registe_agent_with_excepte
}

unregister_agent_id () {
    local skip="$1"
    log unregister_agent_id - "trying to unregister agent id"
    if [ -f "$AGENT_SETUP_PATH/bin/gse_agent" ]; then
        if [ -f "${GSE_AGENT_CONFIG_PATH}" ]; then
            unregister_agent_id_result=$("$AGENT_SETUP_PATH"/bin/gse_agent -f "${GSE_AGENT_CONFIG_PATH}" --unregister 2>&1)
        else
            unregister_agent_id_result=$("$AGENT_SETUP_PATH"/bin/gse_agent --unregister 2>&1)
        fi

        if [[ $? -eq 0 ]]; then
            log unregister_agent_id SUCCESS "unregister agent id succeed"
        else
            if [[ "${skip}" == "SKIP" ]]; then
                warn unregister_agent_id - "unregister agent id failed, but skip it. error: ${unregister_agent_id_result}"
            else
                fail unregister_agent_id FAILED "unregister agent id failed, error: ${unregister_agent_id_result}"
            fi
        fi
    else
        warn unregister_agent_id - "gse_agent file not exists in $AGENT_SETUP_PATH/bin"
    fi
}

is_base64_command_exist() {
    if ! command -v base64 >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

check_healthz_by_gse () {
    local SLEEP_TIME=1 RETRY_COUNT=0

    for i in {0..2}; do
        local result execution_code
        if [ -f "${GSE_AGENT_CONFIG_PATH}" ]; then
            result=$("${AGENT_SETUP_PATH}"/bin/gse_agent -f "${GSE_AGENT_CONFIG_PATH}" --healthz 1)
        else
            result=$("${AGENT_SETUP_PATH}"/bin/gse_agent --healthz 1)
        fi
        execution_code=$?
        if [[ "${execution_code}" -eq 0 ]]; then
            break
        else
            sleep "${SLEEP_TIME}"
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [[ "${RETRY_COUNT}" -ge 3 ]]; then
                log healthz_check INFO "gse_agent healthz check return code: ${execution_code}"
                report_result=$(awk -F': ' '{print $2}' <<< "$result")
                if is_base64_command_exist; then
                    report_result=$(echo "$result" | base64 -w 0)
                else
                    report_result=$(echo "$result" | tr "\"" "\'")
                fi
                log report_healthz INFO "${report_result}"
                fail healthz_check FAILED "gse healthz check failed with retry count: $RETRY_COUNT"
            fi
        fi
    done
    report_result=$(awk -F': ' '{print $2}' <<< "$result")
    if is_base64_command_exist; then
        report_result=$(echo "$result" | base64 -w 0)
    else
        report_result=$(echo "$result" | tr "\"" "\'")
    fi
    log report_healthz - "${report_result}"
    log healthz_check INFO "gse_agent healthz check success"
}

remove_agent_if_exists () {
    local i pids
    local path=${AGENT_SETUP_PATH%/*}/agent

    ! [[ -d $path ]] && return 0
    "$path/bin/gsectl" stop

    for i in {0..10}; do
        read -r -a pids <<< "$(pidof "$path"/bin/gse_agent)"
        if [ ${#pids[@]} -eq 0 ]; then
            break
        elif [ "$i" == 10 ]; then
            kill -9 "${pids[@]}"
        else
            sleep 1
        fi
    done

    for dir in "${PROXY_CLEAN_UP_DIRS[@]}"; do
        rm -rf "$path/$dir"
    done
}

stop_proxy () {
    local i pids

    ! [[ -d $AGENT_SETUP_PATH ]] && return 0
    "$AGENT_SETUP_PATH/bin/gsectl" stop

    for p in "${PROC_LIST[@]}"; do
        for i in {0..10}; do
            read -r -a pids <<< "$(pidof "$AGENT_SETUP_PATH/bin/gse_${p}")"
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
}

clean_up_proxy_directory () {
    for dir in "${PROXY_CLEAN_UP_DIRS[@]}"; do
        rm -rf "${AGENT_SETUP_PATH}"/"${dir}"
    done
}

remove_proxy () {
    log remove_proxy - "trying to remove proxy if exists"
    stop_proxy

    log remove_proxy - "trying to remove old proxy directory(${AGENT_SETUP_PATH}/${PROXY_CLEAN_UP_DIRS[@]})"

    if [[ "$REMOVE" == "TRUE" ]]; then
        unregister_agent_id SKIP
        clean_up_proxy_directory
        log remove_proxy DONE "proxy removed"
        exit 0
    else
        clean_up_proxy_directory
        [[ -d $AGENT_SETUP_PATH ]] && return 0 || return 1
    fi
}

get_config () {
    local filename http_status
    log get_config - "request $NODE_TYPE config file(s)"

    for filename in "${PROXY_CONFIGS[@]}"; do
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
            curl -g -s -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/get_gse_config/ -o "$TMP_DIR/$filename" --silent -w "%{http_code}")
        rm -f "$tmp_json_body" "$tmp_json_resp"

        if [[ "$http_status" != "200" ]]; then
            fail get_config FAILED "request config $filename failed. request info:$CLOUD_ID,$LAN_ETH_IP,$NODE_TYPE,$filename,$TOKEN. http status:$http_status, file content: $(cat "$TMP_DIR/$filename")"
        fi
    done
}

setup_proxy () {
    log setup_proxy START "setting up gse proxy."
    report_mkdir "$AGENT_SETUP_PATH"/etc/

    cd "$AGENT_SETUP_PATH/.." && ( tar xf "$TMP_DIR/$PKG_NAME" || fail setup_proxy FAILED "decompress package $PKG_NAME failed" )

    # setup config file
    get_config

    for f in "${PROXY_CONFIGS[@]}"; do
        if [[ -f $TMP_DIR/$f ]]; then
            log setup_proxy - "copy config file: ${f}"
            cp -fp "$TMP_DIR/$f" proxy/etc/${f}
        else
            fail setup_proxy FAILED "config file ${f} for gse proxy lost. please check."
        fi
    done

    # create dir
    report_mkdir "$GSE_AGENT_RUN_DIR" "$GSE_AGENT_DATA_DIR" "$GSE_AGENT_LOG_DIR"

    register_agent_id

    start_proxy

    # 由于 proxy endpoint 部分通过自身代理，需要等待 proxy 启动后再进行健康检查
    check_healthz_by_gse

    log setup_proxy DONE "gse proxy setup successfully"
}

download_pkg () {
    local f http_status path

    log download_pkg START "download gse agent package from $COMPLETE_DOWNLOAD_URL/$PKG_NAME)."

    if [[ "${REMOVE}" == "TRUE" ]]; then
        log download_pkg - "remove proxy, no need to download package"
        return 0
    fi
    cd "$TMP_DIR" && rm -f "$PKG_NAME"

    for f in $PKG_NAME; do
        http_status=$(http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY curl -g -o "$TMP_DIR/$f" \
                --silent -w "%{http_code}" "$COMPLETE_DOWNLOAD_URL/$f")
        # HTTP status 000需要进一步研究
        if [[ $http_status != "200" ]] && [[ "$http_status" != "000" ]]; then
            fail download_pkg FAILED "file $f download failed. (url:$COMPLETE_DOWNLOAD_URL/$f, http_status:$http_status)"
        fi
    done

    log download_pkg DONE "gse_proxy package download succeeded"
    log report_cpu_arch DONE "${CPU_ARCH}"
}

check_deploy_result () {
    # 端口监听状态
    local ret=0

    AGENT_PID=$( get_pid_by_comm_path gse_agent "$AGENT_SETUP_PATH/bin/gse_agent" "WORKER" )

    is_port_listen_by_pid "$AGENT_PID" "$IO_PORT"  || { fail check_deploy_result FAILED "port $IO_PORT is not listen"; ((ret++)); }
    # is_port_listen_by_pid "$AGENT_PID" $(seq "$BT_PORT_START" "$BT_PORT_END") || { fail check_deploy_result FAILED "bt port is not listen"; ((ret++)); }
    is_port_connected_by_pid "$AGENT_PID" "$IO_PORT" || { fail check_deploy_result FAILED "agent(PID:$AGENT_PID, PORT:$IO_PORT) is not connect to gse server"; ((ret++)); }

    DATA_PID=$( get_pid_by_comm_path gse_data "$AGENT_SETUP_PATH/bin/gse_data" "WORKER" )
    is_port_listen_by_pid "$DATA_PID" "$DATA_PORT"  || { fail check_deploy_result FAILED "port $DATA_PORT is not listen"; ((ret++)); }
    is_port_connected_by_pid "$DATA_PID" "$DATA_PORT" || { fail check_deploy_result FAILED "gse_data(PID:$DATA_PID, PORT:$DATA_PORT) is not connect to gse server"; ((ret++)); }

    [ $ret -eq 0 ] && log check_deploy_result DONE "gse proxy has been deployed successfully"
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
        curl -g -s -S -X POST -d@"$tmp_json_body" "$CALLBACK_URL"/report_log/ -o "$tmp_json_resp"
    rm -f "$tmp_json_body" "$tmp_json_resp"
}

validate_vars_string () {
    echo "$1" | grep -Pq '^[a-zA-Z_][a-zA-Z0-9]+='
}

check_pkgtool () {
    local stderr_to
    stderr_to=$(mktemp "$TMP_DIR"/nm.chkpkg.XXXXX)
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
    local dir=$1
    if df -x tmpfs -x devtmpfs --output=avail -k "$TMP_DIR" | awk 'NR==2 { if ($1 < 300 * 1024 ) { exit 1 } else {exit 0} }'; then
        log check_env  - "check free disk space. done"
    else
        fail check_env FAILED "no enough space left on $dir"
    fi
}

check_dir_permission () {
    mkdir -p "$TMP_DIR" || fail check-env FAILED "custom temprary dir '$TMP_DIR' create failed."

    if ! mktemp "$TMP_DIR/nm.test.XXXXXXXX" &>/dev/null ; then
        rm "$TMP_DIR"/nm.test.????????
        fail check_env FAILED "create temp files failed in $TMP_DIR"
    else
        log check_env  - "check temp dir write access: yes"
    fi
}

check_download_url () {
    local http_status f

    if [[ "${REMOVE}" == "TRUE" ]]; then
        return 0
    fi

    for f in $PKG_NAME; do
         log check_env - "checking resource($COMPLETE_DOWNLOAD_URL/$f) url's validality"
         http_status=$(http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY curl -g -o /dev/null --silent -Iw '%{http_code}' "$COMPLETE_DOWNLOAD_URL/$f")
         if [[ "$http_status" == "200" ]] || [[ "$http_status" == "000" ]]; then
             log check_env - "check resource($COMPLETE_DOWNLOAD_URL/$f) url succeed"
         else
             fail check_env FAILED "check resource($COMPLETE_DOWNLOAD_URL/$f) url failed, http_status:$http_status"
         fi
    done
}

check_target_clean () {
    if [ -d $AGENT_SETUP_PATH/ ]; then
        warn check_env - "directory $AGENT_SETUP_PATH is not clean. everything will be wiped unless -u was specified"
    fi
}

install_depandense () {
    depandense_pkgs=( compat-openssl10 )
    _yum=$(command -v yum 2>/dev/null)
    _apt=$(command -v apt 2>/dev/null)
    _dnf=$(command -v dnf 2>/dev/null)


    if [ -f "${_yum}" ]; then
        _rpm=$(command -v rpm 2>/dev/null)
        if [ -f "${_rpm}" ]; then
            if ! "${_rpm}" -q "${depandense_pkgs[@]}" >/dev/null 2>&1; then
                "${_yum}" --setopt=timeout=2 --setopt=retries=1 -y -q install "${depandense_pkgs[@]}"
            else
                log check_env - "Depandense "${depandense_pkgs[@]}" already installed."
                return 0
            fi
        else
            "${_yum}" --setopt=timeout=2 --setopt=retries=1 -y -q install "${depandense_pkgs[@]}"
        fi
    elif [ -f "${_apt}" ]; then
        apt-get -y install "${depandense_pkgs[@]}"
    elif [ -f "${_dnf}" ]; then
        dnf -y -q install "${depandense_pkgs[@]}"
    fi

    if [ $? -eq 0 ]; then
        log check_env - "Install depandense "${depandense_pkgs[@]}" successful."
    else
        warn check_env - "Install depandense "${depandense_pkgs[@]}" failed, but skip it"
    fi
}


_help () {

    echo "${0%*/} -i CLOUD_ID -l URL -i CLOUD_ID -I LAN_IP [OPTIONS]"

    echo "  -n NAME"
    echo "  -t VERSION"
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
    echo "  -T TEMP directory"
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
    echo "  -F UNREGISTER_AGENT_ID [optional]"

    exit 0
}

check_env () {
    log check_env START "checking prerequisite. NETWORK_POLICY,DISK_SPACE,PERMISSION,RESOURCE etc.[PID:$CURR_PID]"

    check_disk_space "$TMP_DIR"
    check_dir_permission
    check_pkgtool
    check_download_url
    check_target_clean
    install_depandense

    log check_env DONE "checking prerequisite done, result: SUCCESS"
}

# DEFAULT SETTINGS
CLOUD_ID=0
TMP_DIR=/tmp
AGENT_SETUP_PATH="/usr/local/gse/${NODE_TYPE}"
CURR_PID=$$
UPGRADE=false
OVERIDE=false
UNREGISTER_AGENT_ID=false
REMOVE=false
CALLBACK_URL=
AGENT_PID=

# main program
while getopts n:t:I:i:l:s:uc:r:x:p:e:a:k:N:g:v:oT:RO:E:A:V:B:S:Z:K:F arg; do
    case $arg in
        n) export NAME="$OPTARG" ;;
        t) export VERSION="$OPTARG" ;;
        I) export LAN_ETH_IP=$OPTARG ;;
        i) export CLOUD_ID=$OPTARG ;;
        l) export DOWNLOAD_URL=${OPTARG%/} ;;
        s) export TASK_ID=$OPTARG ;;
        u) export UPGRADE=TRUE ;;
        c) export TOKEN=$OPTARG ;;
        r) export CALLBACK_URL=$OPTARG ;;
        x) export HTTP_PROXY=$OPTARG; HTTPS_PROXY=$OPTARG ;;
        p) export AGENT_SETUP_PATH=$(echo $OPTARG/$NODE_TYPE | sed 's|//*|/|g') ;;
        e) export BT_FILE_SERVER_IP=( ${OPTARG//,/ } ) ;;
        a) export DATA_SERVER_IP=( ${OPTARG//,/ } ) ;;
        n) export NAME="$OPTARG" ;;
        t) export VERSION=$OPTARG ;;
        k) export TASK_SERVER_IP=( ${OPTARG//,/ } ) ;;
        N) export UPSTREAM_TYPE=$OPTARG ;;
        v) export VARS_LIST="$OPTARG" ;;
        o) export OVERIDE=TRUE ;;
        T) export TMP_DIR=$OPTARG; mkdir -p $TMP_DIR ;;
        R) export REMOVE=TRUE ;;
        O) export IO_PORT=$OPTARG ;;
        E) export FILE_SVR_PORT=$OPTARG ;;
        A) export DATA_PORT=$OPTARG ;;
        V) export BTSVR_THRIFT_PORT=$OPTARG ;;
        B) export BT_PORT=$OPTARG ;;
        S) export BT_PORT_START=$OPTARG ;;
        Z) export BT_PORT_END=$OPTARG ;;
        K) export TRACKER_PORT=$OPTARG ;;
        F) UNREGISTER_AGENT_ID=TRUE ;;
        *)  _help ;;
    esac
done


## 检查自定义环境变量
for var_name in ${VARS_LIST//;/ /}; do
    validate_vars_string $var_name || fail "$var_name is not a valid name"

    case ${var_name%=*} in
        CLOUD_ID | DOWNLOAD_URL | TASK_ID | CALLBACK_URL | HOST_LIST_FILE | NODEMAN_PROXY | AGENT_SETUP_PATH)
            [ "$OVERIDE" == "TRUE" ] || continue ;;
        VARS_LIST) continue ;;
    esac

    eval "$var_name"
done

LOG_FILE="$TMP_DIR"/nm.${0##*/}.$TASK_ID
DEBUG_LOG_FILE=${TMP_DIR}/nm.${0##*/}.${TASK_ID}.debug

# 获取包名
PKG_NAME=${NAME}-${VERSION}.tgz
COMPLETE_DOWNLOAD_URL="${DOWNLOAD_URL}/agent/linux/${CPU_ARCH}/"
GSE_AGENT_CONFIG_PATH="${AGENT_SETUP_PATH}/etc/${GSE_AGENT_CONFIG}"

# redirect STDOUT & STDERR to DEBUG
exec &> >(tee "$DEBUG_LOG_FILE")

log check_env - "$@"
# 整体安装流程:
#pre_view
for step in check_env \
            download_pkg \
            remove_proxy \
            remove_agent_if_exists \
            setup_proxy \
            check_deploy_result; do
    $step
done
