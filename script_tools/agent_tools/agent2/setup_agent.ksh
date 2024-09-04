#!/bin/ksh
# vim:ft=sh expandtab sts=4 ts=4 sw=4 nu
# gse agent 2.0 安装脚本, 仅在节点管理2.0中使用

# DEFAULT DEFINITION
NODE_TYPE=agent

GSE_AGENT_RUN_DIR=/var/run/gse
GSE_AGENT_DATA_DIR=/var/lib/gse
GSE_AGENT_LOG_DIR=/var/log/gse


GSE_AGENT_CONFIG="gse_agent.conf"
set -A AGENT_CONFIGS gse_agent.conf
set -A AGENT_CLEAN_UP_DIRS bin

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

get_cpu_arch "uname -p" || get_cpu_arch "uname -m"  || arch || fail get_cpu_arch "Failed to get CPU arch, please contact the developer."

# 清理逻辑：保留本次的LOG_FILE,下次运行时会删除历史的LOG_FILE。
# 保留安装脚本本身
cleanup () {
    bulk_report_step_status "$LOG_FILE" "$BULK_LOG_SIZE" URG # 上报所有剩余的日志
    rm -rf /tmp/logpipe

    if ! [[ $DEBUG = "true" ]]; then
        local GLOBIGNORE="$LOG_FILE*"
        for file in "$TMP_DIR"/nm.* ; do
          if [ -e "$file" ]; then
            echo "removing $file"
            rm -r "$file"
          fi
        done
    fi

    exit 0
}

# 打印错误行数信息
report_err () {
    awk -v LN="$1" -v L="ERROR" -v D="$(date +%F\ %T)" \
        'NR>LN-3 && NR<LN+3 { printf "%s %s cmd-return-err %-5d%3s%s\n", D, L, NR, (NR==LN?">>>":""), $0 }' $0
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
        let BT_PORT_START=BT_PORT_START+1
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
        echo 'no gse_master'
    fi

    printf "%d\n" "${pids[@]}"
}

is_base64_command_exist() {
    if ! command -v base64 >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
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

check_heathz_by_gse () {
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
                report_result=$(echo "$result" | awk -F': ' '{print $2}')
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
    report_result=$(echo "$result" | awk -F': ' '{print $2}')
    if is_base64_command_exist; then
        report_result=$(echo "$result" | base64 -w 0)
    else
        report_result=$(echo "$result" | tr "\"" "\'")
    fi
    log report_healthz - "${report_result}"
    log healthz_check INFO "gse_agent healthz check success"
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
        if [[ "${registe_code}" -eq 0 ]] && [[ ! "${registe_result}" == *overwrite* ]]; then
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

clean_up_agent_directory () {
    for dir in "${AGENT_CLEAN_UP_DIRS[@]}"; do
        rm -rf "${AGENT_SETUP_PATH}"/"${dir}"
    done
}

remove_agent () {
    log remove_agent - 'trying to stop old agent'
    stop_agent

    log remove_agent - "trying to remove old agent directory(${AGENT_SETUP_PATH}/${AGENT_CLEAN_UP_DIRS[@]})"

    if [[ "$REMOVE" == "TRUE" ]]; then
        unregister_agent_id
        clean_up_agent_directory
        log remove_agent DONE "agent removed"
        exit 0
    fi
    clean_up_agent_directory
}

get_config () {
    local filename http_status

    log get_config - "request $NODE_TYPE config file(s)"

    for filename in "${AGENT_CONFIGS[@]}"; do
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
            curl -s -g -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/get_gse_config/ -o "$TMP_DIR/$filename" --silent -w "%{http_code}")
        rm -f "$tmp_json_body" "$tmp_json_resp"

        if [[ "$http_status" != "200" ]]; then
            fail get_config FAILED "request config $filename failed. request info:$CLOUD_ID,$LAN_ETH_IP,$NODE_TYPE,$filename,$TOKEN. http status:$http_status, file content: $(cat "$TMP_DIR/$filename")"
        fi
    done
}

setup_agent () {
    log setup_agent START "setup agent. (extract, render config)"
    report_mkdir "$AGENT_SETUP_PATH"/etc

    cd "$AGENT_SETUP_PATH/.." && ( gunzip -dc "$TMP_DIR/$PKG_NAME" | tar xf - || fail setup_proxy FAILED "decompress package $PKG_NAME failed" )

    get_config

    for f in "${AGENT_CONFIGS[@]}"; do
        if [[ -f $TMP_DIR/$f ]]; then
            cp -fp "$TMP_DIR/${f}" "${AGENT_SETUP_PATH}"/etc/${f}
        else
            fail setup_agent FAILED "agent config file ${f} lost. please check."
        fi
    done

    # create dir
    report_mkdir "$GSE_AGENT_RUN_DIR" "$GSE_AGENT_DATA_DIR" "$GSE_AGENT_LOG_DIR"

    register_agent_id

    check_heathz_by_gse

    start_agent

    log setup_agent DONE "gse agent is setup successfully."
}

download_pkg () {
    local f http_status path
    local tmp_stdout tmp_stderr curl_pid
    if [[ "${REMOVE}" == "TRUE" ]]; then
        log download_pkg - "remove agent, no need to download package"
        return 0
    fi

    log download_pkg START "download gse agent package from $COMPLETE_DOWNLOAD_URL/$PKG_NAME)."
    cd "$TMP_DIR" && rm -f "$PKG_NAME"

    for f in $PKG_NAME; do
        http_status=$(http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY curl -O $COMPLETE_DOWNLOAD_URL/$f \
                --silent -w "%{http_code}")
        # HTTP status 000需要进一步研究
        if [[ $http_status != "200" ]] && [[ "$http_status" != "000" ]]; then
            fail download_pkg FAILED "file $f download failed. (url:$COMPLETE_DOWNLOAD_URL/$f, http_status:$http_status)"
        fi
    done

    log download_pkg DONE "gse_agent package download succeeded"
    log report_cpu_arch DONE "${CPU_ARCH}"
}

check_deploy_result () {
    # 端口监听状态
    local ret=0

    get_pid
    is_connected   "$IO_PORT"          || { fail check_deploy_result FAILED "agent(PID:$gse_master) is not connect to gse server"; ((ret++)); }
    is_connected   "$DATA_PORT"          || { fail check_deploy_result FAILED "agent(PID:$gse_master) is not connect to gse server"; ((ret++)); }

    [ $ret -eq 0 ] && log check_deploy_result DONE "gse agent has bean deployed successfully"
}

# 日志行转为json格式函数
log_to_json() {
    local date _time log_level step status message
    local input="$1"

    # 使用 awk 分离各字段
    # 假设 date、_time、log_level、step 和 status 是分隔符之间的字段
    echo "$input" | awk '
        {
            # 假设前五个字段是 date、_time、log_level、step 和 status
            date = $1
            _time = $2
            log_level = $3
            step = $4
            status = $5
            message = ""
            for (i = 6; i <= NF; i++) {
                if (i == 6) {
                    message = $i
                } else {
                    message = message " " $i
                }
            }
            printf("%s %s %s %s %s %s\n", date, _time, log_level, step, status, message)
        }
    ' | {
        read -r date _time log_level step status message

        # 合成完整的日期时间字符串
        datetime="$date $_time"

        # 使用 Perl 计算 Unix 时间戳
        timestamp=$(perl -e 'use Time::Piece; print Time::Piece->strptime($ARGV[0], "%Y-%m-%d %H:%M:%S")->epoch' "$datetime")

        # 输出 JSON 格式
        printf '{"timestamp": "%s", "level": "%s", "step":"%s", "log":"%s","status":"%s"}\n' \
            "$timestamp" "$log_level" "$step" "$message" "$status"
    }
}

# 读入LOG_FILE的日志然后批量上报
# 用法：bulk_report_step_status <log_file> <bulk_size:3> <is_urg>
bulk_report_step_status () {
    local log_file=$1
    local bulk_size=${2:-3} # 默认设置为累积三条报一次
    local is_urg=${3:-""}   # 设置URG后立即上报
    local log_total_line diff
    local bulk_log log line json_log
    local tmp_json_body tmp_json_resp

    # 未设置上报API时，直接忽略
    [[ -z "$CALLBACK_URL" ]] && return 0
    log_total_line=$(wc -l <"$log_file" | tr -d ' ')
    diff=$(( log_total_line - LOG_RPT_CNT ))

    if (( diff >= bulk_size )) || [[ $is_urg = "URG" ]]; then
        LOG_RPT_CNT=$(expr $LOG_RPT_CNT + 1)   #always report from next line
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
    echo "$bulk_log" | while read -r line; do
        log_json=$(log_to_json "$line")
        log[${#log[@]}]=$log_json
    done
    # 生成log json array
    json_log=$(printf "%s," "${log[@]}")
    json_log=${json_log%,}

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
    "logs": [ $json_log ]
}
_OO_

    http_proxy=$HTTP_PROXY https_proxy=$HTTP_PROXY \
        curl -g -s -S -X POST --retry 5 -d@"$tmp_json_body" "$CALLBACK_URL"/report_log/ -o "$tmp_json_resp"
    rm -f "$tmp_json_body" "$tmp_json_resp"
}

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

validate_vars_string () {
    echo "$1" | grep -Pq '^[a-zA-Z_][a-zA-Z0-9_]*='
}

check_pkgtool () {
    local stderr_to
    stderr_to=$(touch /tmp/nm.chkpkg.`date +%s`)
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

    if [[ "${REMOVE}" == "TRUE" ]]; then
        return 0
    fi

    for f in $PKG_NAME; do
         log check_env - "checking resource($COMPLETE_DOWNLOAD_URL/$f) url's validality"
         http_status=$(curl -g -o /dev/null --silent -Iw '%{http_code}' "$COMPLETE_DOWNLOAD_URL/$f")
         if [[ "$http_status" == "200" ]] || [[ "$http_status" == "000" ]]; then
             log check_env - "check resource($COMPLETE_DOWNLOAD_URL/$f) url succeed"
         else
             fail check_env FAILED "check resource($COMPLETE_DOWNLOAD_URL/$f) url failed, http_status:$http_status"
         fi
    done
}

check_target_clean () {
    if [[ -d $AGENT_SETUP_PATH/ ]]; then
        warn check_env - "directory $AGENT_SETUP_PATH is not clean. everything will be wiped unless -u was specified"
    fi
}

_help () {

    echo "${0%*/} -i CLOUD_ID -l URL -I LAN_IP [OPTIONS]"

    echo "  -n NAME"
    echo "  -t VERSION"
    echo "  -I lan ip address on ethernet "
    echo "  -i CLOUD_ID"
    echo "  -l DOWNLOAD_URL"
    echo "  -s TASK_ID. [optional]"
    echo "  -c TOKEN. [optional]"
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
    echo "  -F UNREGISTER_AGENT_ID [optional]"

    exit 0
}

check_env () {
    local node_type=${1:-$NODE_TYPE}

    log check_env START "checking prerequisite. NETWORK_POLICY,DISK_SPACE,PERMISSION,RESOURCE etc.[PID:$CURR_PID]"

    [ "$CLOUD_ID" != "0" ] && node_type=pagent
    validate_setup_path
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
OVERIDE=false
REMOVE=false
UNREGISTER_AGENT_ID=false
CALLBACK_URL=
AGENT_PID=
DEBUG=

# 已上报的日志行数
LOG_RPT_CNT=0
BULK_LOG_SIZE=3

# main program
while getopts n:t:I:i:l:s:uc:r:x:p:e:a:k:N:v:oT:RDO:E:A:V:B:S:Z:K:F arg; do
    case $arg in
        n) NAME="$OPTARG" ;;
        t) VERSION="$OPTARG" ;;
        I) LAN_ETH_IP=$OPTARG ;;
        i) CLOUD_ID=$OPTARG ;;
        l) DOWNLOAD_URL=${OPTARG%/} ;;
        s) TASK_ID=$OPTARG ;;
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
        D) DEBUG=TRUE ;;
        O) IO_PORT=$OPTARG ;;
        E) FILE_SVR_PORT=$OPTARG ;;
        A) DATA_PORT=$OPTARG ;;
        V) BTSVR_THRIFT_PORT=$OPTARG ;;
        B) BT_PORT=$OPTARG ;;
        S) BT_PORT_START=$OPTARG ;;
        Z) BT_PORT_END=$OPTARG ;;
        K) TRACKER_PORT=$OPTARG ;;
        F) UNREGISTER_AGENT_ID=TRUE ;;
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
for var_name in ${VARS_LIST}; do
    validate_vars_string "$var_name" || fail "$var_name is not a valid name"

    case ${var_name%=*} in
        CLOUD_ID | DOWNLOAD_URL | TASK_ID | CALLBACK_URL | HOST_LIST_FILE | NODEMAN_PROXY | AGENT_SETUP_PATH)
            [ "$OVERIDE" == "TRUE" ] || continue ;;
        VARS_LIST) continue ;;
    esac

    eval "$var_name"
done

# 获取包名
PKG_NAME=${NAME}-${VERSION}.tgz
COMPLETE_DOWNLOAD_URL="${DOWNLOAD_URL}/agent/aix/${CPU_ARCH}"
GSE_AGENT_CONFIG_PATH="${AGENT_SETUP_PATH}/etc/${GSE_AGENT_CONFIG}"

LOG_FILE="$TMP_DIR"/nm.${0##*/}.$TASK_ID
DEBUG_LOG_FILE=${TMP_DIR}/nm.${0##*/}.${TASK_ID}.debug

# redirect STDOUT & STDERR to DEBUG
mkfifo /tmp/logpipe
tee "$DEBUG_LOG_FILE" < /tmp/logpipe &
exec > /tmp/logpipe 2>&1

log check_env - "Args are: $*"

# removed remove_crontab、setup_startup_scripts -> 由 gsectl 判断是否添加 / 移除

for step in check_env \
            download_pkg \
            remove_agent \
            remove_proxy_if_exists \
            setup_agent \
            check_deploy_result; do
    $step
done
