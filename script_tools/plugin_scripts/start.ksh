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
    echo "    /usr/local/gse/plugins/bin/start.ksh aixbeat"
    exit 0
}


_status_aix_proc () {
    local proc="$1"
    export pids

    set -A pids $(ps -eo pid,comm| grep "$proc" | grep -v grep | grep -v "start.ksh" | awk '{print $1}')
    echo ${pids[*]}

}

_status () {
    local proc="$1"
    _status_${os_type}_proc $proc
}

case $(uname -s) in
    *AIX) os_type=aix; export LAN_IP=$(get_lan_ip | head -1) ;;
esac

[ -z "$1" ] && usage

log -n "start $1 ..."
if [ -s ./$1 ]; then
    chmod +x ./$1
    if [ ! -f ../etc/${1}.conf ];then
      red_echo "../etc/${1}.conf file not exists!"
      exit 1
    fi
else
    red_echo "$PWD/$1: file not exists!"
    exit 1
fi

# _status $1 > /dev/null

if [[ ${#pids[@]} -eq 0 ]]; then
    nohup ./$1 -c ../etc/${1}.conf >/dev/null  2>/tmp/xuoasefasd.err &
	sleep 10 
    procnum=$(ps -eo pid,comm| grep "$1" | grep -v grep | grep -v "start.ksh" | wc -l) 
    _status $1 > /dev/null
    if [[ ${procnum} -eq 1 ]]; then
        green_echo "Done"
    else
        red_echo "$(< /tmp/xuoasefasd.err). Fail"
        exit 1
    fi
else
    red_echo "${1} processor exists."
    exit 1
fi
