#!/bin/bash

function ceiling {
    DIVIDEND=${1}
    DIVISOR=${2}
    if [ $(( DIVIDEND % DIVISOR )) -gt 0 ]; then
            RESULT=$(( ( ( $DIVIDEND - ( $DIVIDEND % $DIVISOR ) ) / $DIVISOR ) + 1 ))
    else
            RESULT=$(( $DIVIDEND / $DIVISOR ))
    fi
    echo $RESULT
}

VERSION=1.0

ENABLE=
# 分片执行数量
SLICE_NUM=2
# 迁移的订阅任务ID起始
SUB_BEGIN=
# 迁移的订阅任务ID终止
SUB_END=


usage () {
    cat <<EOF
用法:
    该脚本用于节点管理2.0升级至2.1的订阅数据升级迁移
    $PROGRAM [ -h --help -?  查看帮助 ]
    通用参数：
            [ -b, --begin           [必选] "迁移的订阅任务ID起始" ]
            [ -e, --end             [必选] "迁移的订阅任务ID终止" ]
            [ -s, --slice-num       [可选] "迁移任务分片执行数量。默认是$SLICE_NUM" ]
            [ -E, --enable          [可选] "迁移enable=True的订阅任务，默认迁移False" ]
EOF
}

usage_and_exit () {
    usage
    exit "$1"
}

log () {
    echo "$@"
}

error () {
    echo "$@" 1>&2
    usage_and_exit 1
}

warning () {
    echo "$@" 1>&2
    EXITCODE=$((EXITCODE + 1))
}

version () {
    echo "$PROGRAM version $VERSION"
}

# 解析命令行参数，长短混合模式
(( $# == 0 )) && usage_and_exit 1
while (( $# > 0 )); do
    case "$1" in
        -b | --begin )
            shift
            SUB_BEGIN=$1
            ;;
        -e | --end )
            shift
            SUB_END=$1
            ;;
        -s | --slice_num )
            shift
            SLICE_NUM=$1
            ;;
        -E | --enable )
            ENABLE=--enable
            ;;
        --help | -h | '-?' )
            usage_and_exit 0
            ;;
        --version | -v | -V )
            version
            exit 0
            ;;
        -*)
            error "不可识别的参数: $1"
            ;;
        *)
            break
            ;;
    esac
    shift $(($# == 0 ? 0 : 1))
done

LANG="zh_CN.UTF-8"
[ -f "${HOME}"/.bkrc ] && source "${HOME}"/.bkrc
source "${WORKON_HOME}"/bknodeman-nodeman/bin/activate
cd "${BK_HOME}"/bknodeman/nodeman


# 订阅ID范围
sub_begin=$SUB_BEGIN
sub_end=$SUB_END


log_root="/tmp/node_man_upgrade_${sub_begin}_${sub_end}_$(date "+%Y%m%d-%H%M%S")"

if [[ $ENABLE = --enable ]]; then
    log_root=${log_root}_enable
fi

mkdir -p $log_root

echo "transfer_old_sub's log save to ${log_root}"

# 分片数量
slice_num=$SLICE_NUM

begin=$sub_begin
limit=$( ceiling $(($sub_end-$sub_begin+1)) $slice_num)

while [ $begin -le $sub_end ]
do
  end=$(($begin+$limit))
  command="nohup ./bin/manage.sh transfer_old_sub $begin $end $ENABLE >> ${log_root}/transfer_old_sub_${begin}_${end}.log 2>&1 &"
  eval $command
  begin=$(($end+1))
done

jobs


check_command="grep -E '.*([[:digit:]]+[[:space:]]/[[:space:]][[:digit:]]+|total_cost)' ${log_root}/transfer_old_sub_*"

echo "check_command -> ${check_command}"
