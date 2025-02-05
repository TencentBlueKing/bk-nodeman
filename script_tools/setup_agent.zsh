#!/bin/zsh
# vim:ft=sh expandtab sts=4 ts=4 sw=4 nu
# gse agent安装脚本, 仅在节点管理2.0中使用

# DEFAULT DEFINITION
NODE_TYPE=agent

GSE_AGENT_RUN_DIR=/var/run/gse
GSE_AGENT_DATA_DIR=/var/lib/gse
GSE_AGENT_LOG_DIR=/var/log/gse
BACKUP_CONFIG_FILES=("procinfo.json")
OS_INFO=""
OS_TYPE=""
CURL_PATH=""

# 收到如下信号或者exit退出时，执行清理逻辑
#trap quit 1 2 3 4 5 6 7 8 10 11 12 13 14 15
trap 'cleanup' HUP INT QUIT ABRT SEGV PIPE ALRM TERM EXIT

report_step_status () {
    # local date _time log_level step status message
    # local tmp_json_body tmp_json_resp

    # 未设置上报API时，直接忽略
    [ -z "$CALLBACK_URL" ] && return 0

    # echo "$@" | read  date _time log_level step status message
    echo "$@" | read  date _time log_level step

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
get_cpu_arch () {
    local cmd=$1
    CPU_ARCH=$(eval $cmd)
    CPU_ARCH=$(echo ${CPU_ARCH} | tr 'A-Z' 'a-z')
    if [[ "${CPU_ARCH}" =~ ^i[3456]86 ]]; then
        CPU_ARCH="x86"
        return 0
    elif [[ "${CPU_ARCH}" =~ "arm" ]]; then
        CPU_ARCH="arm64"
        return 0
    else
        return 1
    fi
}

get_cpu_arch "uname -m" || get_cpu_arch "uname -p"  || arch || fail get_cpu_arch "Failed to get CPU arch, please contact the developer."

PKG_NAME=gse_client-mac-${CPU_ARCH}.tgz


get_daemon_file () {
    daemon_fill_path="/Library/LaunchDaemons/"
    setup_path=$(echo ${AGENT_SETUP_PATH%*/} | tr '\/' '.')
    DAEMON_FILE_NAME="com.tencent.gse_${NODE_TYPE}${setup_path}.Daemon.plist"
}


# 清理逻辑：保留本次的LOG_FILE,下次运行时会删除历史的LOG_FILE。
# 保留安装脚本本身
cleanup () {
    report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" URG # 上报所有剩余的日志

    if ! [[ $DEBUG = "true" ]]; then
        local GLOBIGNORE="$LOG_FILE*"
        rm -vf "$TMP_DIR"/nm.*
    fi

    exit 0
}


validate_setup_path () {
    local invalid_path_prefix=(
        /tmp
        /var
        /etc
        /lib
        /dev
        /sbin
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

    for p in $invalid_path; do
        if [[ "${p2}" == "$p" ]]; then
            fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
        fi
    done

    for p in $invalid_path_prefix; do
        if [[ "${p2//$p}" != "$p2" ]]; then
            fail check_env FAILED "$AGENT_SETUP_PATH is not allowed to install agent"
        fi
    done
}

is_port_listen () {
    local i port

    for i in {0..15}; do
        sleep 1
        for port in $*; do
            lsof -iTCP:"$port" -sTCP:LISTEN -a -i -P -n -p "$AGENT_PID" && return 0
        done
    done

    return 1
}

# 判断某个pid是否监听指定的端口列表
# 利用linux内核/proc/<pid>/net/tcp文件中第四列0A表示LISTEN
# 第二列16进制表达的ip和port
is_port_listen_by_pid () {
    local pid regex stime
    pid=$1
    shift 1

    if [ `lsof -n -i | grep -e LISTEN -e ESTABLISHED | wc -l` -le 5000 ];then
        stime=1
    else
        stime=0
    fi

    for i in {0..10}; do
        echo ------ $i  `date '+%c'`
        sleep 1
        for port in $*; do
            if [ $stime -eq 1 ];then
                echo need to sleep 1s
                sleep 1
            fi
            echo ------ $port  `date '+%c'`
            if netstat -anv | awk '{print $4,$6,$9}' | grep -w $port | grep LISTEN | grep -w $pid > /dev/null; then
                return 0
            fi
        done
    done
    return 1
}

is_port_connected_by_pid () {
    local pid port regex
    pid=$1 port=$2

    for i in {0..10}; do
        sleep 1
        if netstat -anv | awk '{print $4,$6,$9}' | grep -w $port | grep ESTABLISHED | grep -w $pid >/dev/null; then
            return 0
        fi
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
   $AGENT_SETUP_PATH/../plugins/bin/gsecmdline -d 1430 -s test
}

# 用法：通过ps的comm字段和二进制的绝对路径来精确获取pid
get_pid_by_comm_path () {
    local comm=$1 comm_path=$2
    local _pids pids
    local pid
    echo xxx $comm
    _pids=$(ps -c -eo gid,command | grep -w $comm | awk '{print $1}')

    # 传入了绝对路径，则进行基于二进制路径的筛选
    if [[ -e "$comm_path" ]]; then
        for pid in $_pids; do
            if [[ $(ps -eo pid,ppid,comm | grep -w "$pid" | awk '{print $3}') == $comm_path ]]; then
                pids+=($pid)
            fi
        done
    else
        pids=($_pids)
    fi

    echo $pids
}

is_process_ok () {
    local proc=${1:-agent}
    local gse_master gse_workers
    local gse_master_pids
    gse_master_pids="$( get_pid_by_comm_path gseMaster "$AGENT_SETUP_PATH/bin/gse_${proc}" | xargs)"
    gse_master=$gse_master_pids
    gse_workers=$( get_pid_by_comm_path "${proc}Worker" "$AGENT_SETUP_PATH/bin/gse_${proc}" | xargs)
    if [ ${#gse_master} -eq 0 ]; then
        fail setup_agent FAILED "process check: no gseMaster found. gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    if [ ${#gse_master} -gt 1 ]; then
        fail setup_agent FAILED "process check: ${#gse_master} gseMaster found. pid($gse_master_pids) gse_${proc} process abnormal (node type:$NODE_TYPE)"
    fi

    # worker 进程在某些任务情况下可能不只一个，只要都是一个爹，多个worker也是正常，不为0即可
    if [ "${#gse_workers}" -eq 0 ]; then
        fail setup_agent FAILED "process check: ${proc}Worker not found (node type:$NODE_TYPE)"
    fi
}

# 没有python解释器的mac os可认定为系统本身有问题
# 通过系统python代替telnet或者linux的socket探测方式
get_python_path () {
    local python_path
    if which python3 > /dev/null; then
        python_path=$(which python3)
    else
        python_path=$(which python)
	fi
    echo $python_path
}

is_target_reachable () {
    local ip="$1"
    local target_port="$2"
    local _port err timeout_exist

    if [[ $target_port =~ [0-9]+-[0-9]+ ]]; then
        ports=( $(seq $(echo ${target_port//-/ } ) ) )
    else
        ports=( "$target_port" )
    fi

    # 判断timeout命令是否存在
    hash timeout 2>/dev/null
    case $? in
        0) timeout_exist=0 ;;
        1) timeout_exist=1 ;;
    esac

    python_path=$(get_python_path)

    for _port in $ports; do
        if [ "$timeout_exist" -eq 0 ]; then
            timeout 5 $python_path  -c "import socket;client_socket=socket.socket();client_socket.connect(('$ip', $_port))"
        else
            $python_path  -c "import socket;client_socket=socket.socket();client_socket.connect(('$ip', $_port))"
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

    # 非直连Agent的上级节点是所属管控区域的proxy
    for ip in $TASK_SERVER_IP; do
        log check_env - "check if it is reachable to port $IO_PORT of $ip($UPSTREAM_TYPE)"
        is_target_reachable "$ip" "$IO_PORT"
    done

    for ip in $DATA_SERVER_IP; do
        log check_env - "check if it is reachable to port $DATA_PORT of $ip($UPSTREAM_TYPE)"
        is_target_reachable "$ip" "$DATA_PORT"
    done

    for ip in $BT_FILE_SERVER_IP; do
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
    for ip in $TASK_SERVER_IP; do
        log check_env - "check if it is reachable to port $IO_PORT of $ip(${UPSTREAM_TYPE:-GSE_TASK_SERVER})"
        is_target_reachable "$ip" "$IO_PORT"
    done

    for ip in $DATA_SERVER_IP; do
        log check_env - "check if it is reachable to port $DATA_PORT of $ip(${UPSTREAM_TYPE:-GSE_DATA_SERVER})"
        is_target_reachable "$ip" "$DATA_PORT"
    done

    for ip in $BT_FILE_SERVER_IP; do
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
    if [ $IS_SUPER == false ]; then
        return
    fi

    local tmpcron
    tmpcron=$(mktemp "$TMP_DIR"/cron.XXXXXXX)

    # 仅删除关联到安装目录的 crontab，避免多 Agent 互相影响
    crontab -l | grep -v "${AGENT_SETUP_PATH}"  >"$tmpcron"
    crontab "$tmpcron" && rm -f "$tmpcron"

    # 下面这段代码是为了确保修改的crontab能立即生效
    if pgrep -x crond &>/dev/null; then
        pkill -HUP -x crond
    fi
}

setup_startup_scripts () {
    if [ $IS_SUPER == false ]; then
        return
    fi

    get_daemon_file
    local damonfile=$DAEMON_FILE_NAME

    cat >$damonfile << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.tencent.gse_agent.Daemon</string>
	<key>ProgramArguments</key>
	<array>
		<string>${AGENT_SETUP_PATH}/bin/gse_${NODE_TYPE}</string>
		<string>-protect</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>StartInterval</key>
	<integer>180</integer>
	<key>KeepAlive</key>
	<dict>
		<key>SuccessfulExit</key>
		<false/>
	</dict>
</dict>
</plist>
EOF
}

start_agent () {
    local i p

    "$AGENT_SETUP_PATH"/bin/gsectl start || fail setup_agent FAILED "start gse agent failed"

    sleep 3
    is_process_ok agent
}

pidof () {
    path=$1
    ps -eo pid,comm |grep $path |awk '{print $1}'
}

remove_proxy_if_exists () {
    local i pids
    local path=${AGENT_SETUP_PATH%/*}/proxy

    ! [[ -d $path ]] && return 0
    "$path/bin/gsectl" stop

    for p in agent transit btsvr; do
        for i in {0..10}; do
            pids="$(pidof "$path"/bin/gse_${p})"
            if [ ${#pids} -eq 0 ]; then
                # 进程已退，继续检查下一个进程
                break
            elif [ "$i" == 10 ]; then
                # 强杀
                kill -9 $pids
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
        if [[ ${#pids} -eq 0 ]]; then
            log remove_agent SUCCESS 'old agent has been stopped successfully'
            break
        elif [[ $i -eq 10 ]]; then
            kill -9 $pids
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
    log remove_agent - "trying to remove old agent directory(${AGENT_SETUP_PATH})"

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

    for filename in $config; do
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
            $CURL_PATH -s -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/get_gse_config/ -o "$TMP_DIR/$filename" --silent -w "%{http_code}")
        rm -f "$tmp_json_body" "$tmp_json_resp"

        if [[ "$http_status" != "200" ]]; then
            fail get_config FAILED "request config $filename failed. request info:$CLOUD_ID,$LAN_ETH_IP,$NODE_TYPE,$filename,$TOKEN. http status:$http_status, file content: $(cat "$TMP_DIR/$filename")"
        fi
    done
}

setup_agent () {
    log setup_agent START "setup agent. (extract, render config)"
    mkdir -p "$AGENT_SETUP_PATH"

    cd "$AGENT_SETUP_PATH/.." && tar xf "$TMP_DIR/$PKG_NAME"

    if [ $IS_SUPER == true ]; then
        # update gsecmdline under /bin
        cp -fp plugins/bin/gsecmdline /usr/bin/
        # 注意这里 /bin/ 可能是软链
        cp -fp plugins/etc/gsecmdline.conf /usr/bin/../etc/
        chmod 775 /bin/gsecmdline
    fi

    # setup config file
    get_config

    recovery_config_file

    local config=(agent.conf)
    for f in $config; do
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

download_pkg () {
    local f http_status
    local tmp_stdout tmp_stderr curl_pid

    log download_pkg START "download gse agent package from $DOWNLOAD_URL/$PKG_NAME)."
    cd "$TMP_DIR" && rm -f "$PKG_NAME" "agent.conf.$LAN_ETH_IP"

    echo $(date)

    for f in $PKG_NAME; do
        tmp_stdout=$(mktemp "${TMP_DIR}"/nm.curl.stdout_XXXXXXXX)
        tmp_stderr=$(mktemp "${TMP_DIR}"/nm.curl.stderr_XXXXXXXX)
        $CURL_PATH --connect-timeout 5 -o "$TMP_DIR/$f" \
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
    is_port_connected_by_pid "$AGENT_PID"  "$IO_PORT" || { fail check_deploy_result FAILED "agent(PID:$AGENT_PID) is not connect to gse server"; ((ret++)); }

    [ $ret -eq 0 ] && log check_deploy_result DONE "gse agent has been deployed successfully"
}


validate_vars_string () {
    echo "$1" | grep -Pq '^[a-zA-Z_][a-zA-Z0-9_]*='
}

check_pkgtool () {
    _brew=$(command -v brew)
    _curl=$(command -v curl)

    if [ -f "$_curl" ]; then
        CURL_PATH=$_curl
        return 0
    else
        log check_env - "trying to install curl by package management tool"
        if [ -f $TMP_DIR/curl ]; then
            CURL_PATH=$TMP_DIR/curl
        elif [ -f "$_brew" ]; then
            brew install curl | fail check_env FAILED "install curl failed"
            CURL_PATH=$(command -v curl)
        else
            fail check_env FAILED "no curl command found and can not be installed by brew and not found curl in $TMP_DIR"
        fi

        log check_env - "curl has been installed"
    fi
    echo "curl $CURL_PATH"
}

check_disk_space () {
    local dir=$1
    if df -k -t nodevfs "$TMP_DIR" | awk 'NR==2 { if ($2 < 300 * 1024 ) { exit 1 } else {exit 0} }'; then
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
         http_status=$($CURL_PATH -o /dev/null --silent -Iw '%{http_code}' "$DOWNLOAD_URL/$f")
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

check_mac_os () {
    if [[ ! $(command -v sw_vers) ]]; then
        fail check_env FAILED "check mac os failed. witchout sw_vers command here."
    fi
}

check_env () {
    local node_type=${1:-$NODE_TYPE}

    log check_env START "checking prerequisite. NETWORK_POLICY,DISK_SPACE,PERMISSION,RESOURCE etc.[PID:$CURR_PID]"

    [ "$CLOUD_ID" != "0" ] && node_type=pagent
    check_mac_os
    check_pkgtool
    validate_setup_path
    check_polices_${node_type}_to_upstream
    check_disk_space "$TMP_DIR"
    check_dir_permission
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
        e) BT_FILE_SERVER_IP=("${OPTARG//,/ }") ;;
        a) DATA_SERVER_IP=("${OPTARG//,/ }") ;;
        k) TASK_SERVER_IP=("${OPTARG//,/ }") ;;
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

IS_SUPER=true
if sudo -n true 2>/dev/null; then
    IS_SUPER=true
else
    IS_SUPER=false
fi

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
# exec &> >(tee "$DEBUG_LOG_FILE")

log check_env - "Args are: $*"
for step in check_env \
            download_pkg \
            remove_agent \
            remove_proxy_if_exists \
            setup_agent \
            setup_startup_scripts \
            check_deploy_result; do
    $step
done
