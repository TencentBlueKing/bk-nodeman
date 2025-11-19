#!/bin/ksh

red_echo ()      { [ "$HASTTY" != "1" ] && echo "$@" || echo -e "\033[031;1m$@\033[0m"; }
blue_echo ()     { [ "$HASTTY" != "1" ] && echo "$@" || echo -e "\033[034;1m$@\033[0m"; }
green_echo ()    { [ "$HASTTY" != "1" ] && echo "$@" || echo -e "\033[032;1m$@\033[0m"; }

usage () {
    echo "usage: $0 PLUGIN_NAME"
    echo "/usr/local/gse/plugins/bin/reload.ksh aixbeat"
    exit 0
}

get_lan_ip () {
   #
   ifconfig -a | \
       awk -F'[ /\t]+' '/inet/{
               split($3, N, ".")
               if ($3 ~ /^192.168/) {
                   print $3
               }
               if (($3 ~ /^172/) && (N[2] >= 16) && (N[2] <= 31)) {
                   print $3
               }
               if ($3 ~ /^10\./) {
                   print $3
               }
          }'

   return $?
}

cd $(dirname $0) 2>/dev/null
[ -z "$1" ] && usage

case $(uname -s) in
    *AIX) os_type=aix; export LAN_IP=$(get_lan_ip | head -1) ;;
esac

_status_aix_proc () {
    local proc="$1"
    export pids

    set -A pids $(ps -ef | grep -E -w "${proc} -c ../etc/${proc}.conf" | grep -v grep | grep -v "start.ksh" | awk '{print $2}')
    echo ${pids[*]}

}

log () {
     # 打印消息, 并记录到日志, 日志文件由 LOG_FILE 变量定义
     local retval=$?
     local timestamp=$(date +%Y%m%d-%H%M%S)
     local level=INFO
     local func_seq=$(echo ${FUNCNAME[@]} | sed 's/ /-/g')
     local logfile=${LOG_FILE:=/tmp/bkc.log}
   
     local opt=

     if [ "${1}" == "-n" ]; then
          shift 1
          opt=$1
     else
          opt=""
     fi

     echo $opt "[$(blue_echo $LAN_IP)]$timestamp $@"
     echo $opt "[$(blue_echo $LAN_IP)]$timestamp $level|${func_seq} $@" >>$logfile

     return $retval
}

log -n "reload $1 ..."
kill -USR1 $(_status_${os_type}_proc $1) 2>/dev/null
sleep 2
procnum=$(ps -ef | grep -E -w "${1} -c ../etc/${1}.conf" | grep -v grep | wc -l)
if [[ ${procnum} -eq 1 ]]; then
    green_echo ".Done"
else
    red_echo ".Fail"
fi
