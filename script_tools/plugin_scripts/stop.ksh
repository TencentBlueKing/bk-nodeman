#!/bin/ksh

cd $(dirname $0)

red_echo ()      { echo "\033[0;31;1m$@\033[1;37m"; }
blue_echo ()     { echo "\033[0;34;1m$@\033[1;37m"; }
green_echo ()    { echo "\033[0;32;1m$@\033[1;37m"; }

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

usage () {
    echo "usage: $0 PLUGIN_NAME"
    echo "    /usr/local/gse/plugins/bin/stop.ksh aixbeat"
    exit 0
}

_status_aix_proc () {
    local proc="$1"
    local pids

    set -A pids $(ps -ef | grep -E -w "${proc} -c ../etc/${proc}.conf" | grep -v grep | grep -v "stop.ksh " | grep -v "restart.ksh" | awk '{print $2}')
    echo ${pids[*]}

}

_stop () {
    kill -9 $(_status_${os_type}_proc $1) 2>/dev/null
}

_status () {
    local proc="$1"
    _status_${os_type}_proc $proc
}

case $(uname -s) in
    *AIX) os_type=aix; export LAN_IP=$(get_lan_ip | head -1) ;;
esac

[ -z "$1" ] && usage

if [ -s ./$1 ]; then
    chmod +x ./$1
else
    red_echo "$PWD/$1: file not exists!"
    exit 1
fi

log -n "stop $1 ..."
_stop $1
sleep 5
procnum=$(ps -ef | grep -E -w "${1} -c ../etc/${1}.conf" | grep -v grep | grep -v "restart.ksh" | grep -c -v "stop.ksh ")
if [[ ${procnum} -eq 0 ]]; then
    green_echo ".Done"
else
    red_echo ".Fail"
fi
