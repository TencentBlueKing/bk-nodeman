[2025-05-22 14:43:50][PID:10134] job_start
#!/bin/sh

#version 0.00.02

##################
# Configurations #
##################

BASE_PATH="/data/home/user00"
TMP_PATH="${BASE_PATH}/tmp"

SERVERLIST="${BASE_PATH}/zt/version/serverlist.xml"

PIDFILE_PREFIX="${BASE_PATH}/pidfile/scenes.pid"
PIDFILE=${PIDFILE_PREFIX}.$2

LOCK_TIMEOUT=120
WAIT_TIMEOUT=80

type=ScenesServer
sig="-2"

HOST_ADDR="`/sbin/ifconfig eth1 | egrep -o 'inet\saddr:([^\s]*)\s' | egrep -o '[\.0-9]*'`"


#############
# Functions #
#############

log_info() {
	echo "[`date +"%Y-%m-%d %H:%M:%S"`] $@"
}

log_warning() {
	echo "[`date +"%Y-%m-%d %H:%M:%S"`] [WARNING] $@"
}

log_error() {
	echo "[`date +"%Y-%m-%d %H:%M:%S"`] [ERROR] $@"
}

get_inst_pid() {
	PORT=`expr 30119 + $1`
	RESULT=`lsof -i:$PORT | awk '/LISTEN/{print $2}' 2>&1`
	echo $RESULT
}

#CHECK PROCESS
check() {
	PID=`get_inst_pid $1`
	if [ ! -z "${PID}" ]; then
		log_info "$type.$1 is running..."
		exit 1
	else
		log_info "$type.$1 is not running."
	fi
}

get_local_ports() {
	grep "\"$HOST_ADDR\"" $SERVERLIST | egrep -o "301(2[0-9]|30)" | sort | uniq
}

# release_lock() {
# 	rm -rf $LOCK_DIR
# 	if [ $# -ne 0 ]; then
# 		log_info "[WARNING] lock force released."
# 	else
# 		log_info "lock released."
# 	fi
# }

get_lock() {
	# mkdir $LOCK_DIR > /dev/null 2>&1
	# RETVAL=$?

	# i=1
	# while [ $RETVAL -ne 0 ]; do
	# 	sleep 1

	# 	if [ $i -gt $LOCK_TIMEOUT ]; then
	# 		log_info "[WARNING] lock timeout."
	# 		release_lock force
	# 	fi
	# 	i=`expr $i + 1`

	# 	mkdir $LOCK_DIR > /dev/null 2>&1
	# 	RETVAL=$?
	# done
	for port in `get_local_ports`; do
		IS_EXIST=`lsof -i:$port | awk '/LISTEN/{print $2}' 2>&1`
	
		INST_ID=`expr $port - 30119`

		if [ $1 -eq $INST_ID ]; then
			break
		fi
	
		i=1
		while [ -z "${IS_EXIST}" ]; do
			sleep 1
	
			if [ $i -gt $LOCK_TIMEOUT ]; then
				log_error lock timeout. due to sc`printf "%02d" $INST_ID` not exist.
				exit 1
			fi
	
			IS_EXIST=`lsof -i:$port | awk '/LISTEN/{print $2}' 2>&1`
			i=`expr $i + 1`
		done
	done

	log_info "lock acquired."
}


#cmdstatus check
cmdstat()
{
        if [ $? != 0 ]
        then
                exit
        fi
}


start()
{
        ulimit -c unlimited;cd /data/home/user00/zt/version/ ; export LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH;export ASAN_OPTIONS=alloc_dealloc_mismatch=0:distable_coredump=1:disable_core=0:abort_on_error=1:sleep_before_dying=0:detect_leaks=0:symbolize=0;export UBSAN_OPTIONS=print_stacktrace=1;/data/home/user00/zt/version/$type -d > /data/home/user00/log/$type.err 2>&1
        if [ $? == 0 ]
                then
                       echo "$type start ...... [Finished]"
                       #pid_nu=`ps x |grep -v grep |grep $type |awk '{print $1}'`
                       #sleep 3
                       pid_nu=`get_inst_pid $1`
                       i=1
                       while [ -z "$pid_nu" ]; do
                           sleep 1
                           if [ $i -gt $WAIT_TIMEOUT ]; then
                               log_info "$type.$1 start failed. wait timeout(${WAIT_TIMEOUT}s)."
                               exit 1
                           fi
                           i=`expr $i + 1`
                           pid_nu=`get_inst_pid $1`
                       done
                       echo  $pid_nu >"$PIDFILE"
                 else
                        echo "$type start failed. return code not zero."
                        exit 1

        fi
}

stop()
{
        pid_nu=$(get_inst_pid $1)
        ulimit -c unlimited;cd /data/home/user00/zt/version/ ; kill $sig $pid_nu 1>/dev/null 
        i=1
        while [ "$i" -le "6" ]

        do
                ps fx|grep -v grep |grep $type |grep $pid_nu >/dev/null
                if [ $? -eq 0 ]
                then
                        echo "$type.$1 still alive ......"
                        i=$(($i+1))
                        time=$(($i*10-10))
                        sleep  10
                else
                        echo "$type.$1 stop ...... [Finished]"
                        break
                        exit 0
                fi
                if [ $i == 6 ]
                then

                ps fx|grep -v grep |grep $type|grep $pid_nu >/dev/null
                if [ $? -eq 0 ]
                then
                      echo "time consuming ${time}S ........"   
                      echo "$type.$1 stop fail ......"
                          

                        break
                        exit 1
                 else
                        echo "$type.$1  stop  ...... [Finished]"
                        break
                        exit 0
                fi
                      fi
        done
}

reload()
{
        pid_nu=$(get_inst_pid $1)
        ulimit -c unlimited;cd /data/home/user00/zt/version/ ; kill -HUP $pid_nu 1>/dev/null 
        if [ $? != 0 ]
                then
                        echo "$type.$1 reload ...... [Fail]"
                        exit 1
                else
                        echo "$type.$1 reload ...... [Finished]"
                        exit 0
                fi
}

kill9()
{
        pid_nu=$(get_inst_pid $1)
        ulimit -c unlimited;cd /data/home/user00/zt/version/ ; kill -9 $pid_nu 1>/dev/null 
        i=1
        j=1
        while( i==1 )
        do
                ps x|grep -v grep |grep $type|grep $pid_nu >/dev/null
                if [ $? = 0 ]
                then
                        echo "$type.$1 still alive ......"
                        let j+=1
                        sleep 10
                else
                        echo "Kill -9 $type.$1 stop ...... [Finished]"
                        break
                fi
                if [ $j == 10 ]
                then
                        echo "$type.$1 still alive ......"
                        echo "Kill -9 $type.$1 stop error !!!"
                        exit 1
                else
                        echo "$type.$1 stop ...... [Finished]"
                        exit 0
                fi
        done
}

update_pid() {
	for i in `seq 12`; do
		pid_nu=`get_inst_pid $i`
		if [ ! -z "${pid_nu}" ]; then
			PIDFILE=${PIDFILE_PREFIX}.sc`printf "%02d" $i`
			echo $pid_nu > $PIDFILE
		fi
	done
}

validate_inst_id() {
	INST_ID=$1
	INST_ID_ORIG=$2
	if [ $INST_ID -eq 0 ]; then
		if [ -z "${INST_ID_ORIG}" ]; then
			log_info "[ERROR] empty param: module_name"
		else
			log_info "[ERROR] invalid param: \"${INST_ID_ORIG}\""
		fi
		exit 1
	fi
}


#############
# Main loop #
#############

INST_ID_ORIG=$2
INST_ID=${INST_ID_ORIG#sc}
typeset -i INST_ID
INST_ID=${INST_ID#0}


case $1 in
	start)
		validate_inst_id "$INST_ID" "$INST_ID_ORIG"
		check $INST_ID
		get_lock $INST_ID
		start $INST_ID
		;;
	stop)
		validate_inst_id "$INST_ID" "$INST_ID_ORIG"
		stop $INST_ID
		;;
	restart)
		validate_inst_id "$INST_ID" "$INST_ID_ORIG"
		stop $INST_ID
		check $INST_ID
		get_lock $INST_ID
		start $INST_ID
		;;
	reload)
		validate_inst_id "$INST_ID" "$INST_ID_ORIG"
		reload $INST_ID
		;;
	kill9)
		validate_inst_id "$INST_ID" "$INST_ID_ORIG"
		kill9 $INST_ID
		;;
	check)
		validate_inst_id "$INST_ID" "$INST_ID_ORIG"
		check $INST_ID
		;;
	update-pid)
		update_pid
		;;
	*)
		echo "usage: $0 {start|stop|restart|reload|kill9}"
		exit 1
		;;
esac
