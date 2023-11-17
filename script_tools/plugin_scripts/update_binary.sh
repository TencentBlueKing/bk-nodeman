#!/bin/bash

usage () {
    echo "usage: update_binary OPTIONS"
    echo "OPTIONS"
    echo "  -t  plugin category, cloud be: official/external/scripts"
    echo "  -r  uninstall"
    echo "  -m  upgrade type: append or override"
    echo "  -n  plugin name"
    echo "  -f  package of plugin"
    echo "  -p  home path of plugin"
    echo "  -i  plugin group id, for external plugin only"
    #echo "  -v  plugin VERSION, for verification"

    exit 1
}

backup () {
    local backup_filename=${PLUGIN_NAME}-backup.pz

    tar zcPf ${backup_filename} $BINDIR $ETCDIR
    mkdir -p ${BACKUP_DIR}
    mv ${backup_filename} ${BACKUP_DIR}
}

guess_target_dir () {
    case $CATEGORY in
        OFFICIAL | 1)
            export BINDIR=$GSE_HOME/plugins/bin
            export ETCDIR=$GSE_HOME/plugins/etc
            ;;
        EXTERNAL | 2)
            if [ -n "$GROUP_DIR" ]; then
                # 如果提供了实例ID，则将插件安装到给定的ID目录下
                export BINDIR=$GSE_HOME/external_plugins/$GROUP_DIR/$PLUGIN_NAME/
                export ETCDIR=$GSE_HOME/external_plugins/$GROUP_DIR/$PLUGIN_NAME/etc
                export EXTERNAL_PLUGIN_TMPDIR=${EXTERNAL_PLUGIN_DIR}/external_plugins/${GROUP_DIR}/${PLUGIN_NAME}/
                mkdir -p ${EXTERNAL_PLUGIN_TMPDIR}
            else
                export BINDIR=$GSE_HOME/external_plugins/$PLUGIN_NAME/
                export ETCDIR=$GSE_HOME/external_plugins/$PLUGIN_NAME/etc
            fi
            ;;
        SCRIPTS | 3)
            export BINDIR=$GSE_HOME/external_scripts/
            export ETCDIR=$GSE_HOME/external_scripts/
            ;;
        *)
            echo "unknown category $CATEGORY. abort"
            exit 1
            ;;
    esac
}

REMOVE=0
UPGRADE_TYPE=append
RESERVE_CONF=0
TMP=/tmp/
BACKUP_DIR=/tmp/nodeman_backup/
EXTERNAL_PLUGIN_DIR=/tmp/nodeman_external_plugins/

while getopts rut:T:d:n:m:f:z:v:p:h:i: arg; do
    case $arg in
        T)  TIMEOUT=$OPTARG ;;
        t)  export CATEGORY=$OPTARG ;;
        r)  export REMOVE=1 ;;
        m)  export UPGRADE_TYPE=$OPTARG ;;
        n)  export PLUGIN_NAME=${OPTARG} ;;
        p)  export GSE_HOME=${OPTARG} ;;
        z)  export TMP=${OPTARG} ;;
        u)  export RESERVE_CONF=1 ;;
        #v)  export VERSION=$OPTARG ;;
        f)  export PACKAGE=$OPTARG ;;     # 官方插件/第三方插件有效
        i)  export GROUP_DIR=$OPTARG ;;
        *)  usage ;;
    esac
done

CATEGORY=$(echo $CATEGORY | tr 'a-z' 'A-Z')
UPGRADE_TYPE=$(echo $UPGRADE_TYPE | tr 'a-z' 'A-Z')
guess_target_dir
CATEGORY=$(echo $CATEGORY | tr 'a-z' 'A-Z')
UPGRADE_TYPE=$(echo $UPGRADE_TYPE | tr 'a-z' 'A-Z')

if [ "$REMOVE" == 1 ]; then
    cd $BINDIR/ || { echo "$PLUGIN_NAME is not installed, abort"; exit 0; }
    # ./stop.sh ${PLUGIN_NAME} || echo "stop plugin $PLUGIN_NAME failed, ignored."

    if [ "${CATEGORY}" == "OFFICIAL" ]; then
        rm -rf $BINDIR/bin/${PLUGIN_NAME} $ETCDIR/${PLUGIN_NAME}.conf
    else
        rm -rf $BINDIR/
    fi
    exit $?
fi


mkdir -p $GSE_HOME

if [ -d "$BINDIR" ]; then
    backup $PLUGIN_NAME

    if [ "${UPGRADE_TYPE}" != "APPEND" -a "${CATEGORY}" != "OFFICIAL" ]; then
        echo "removing old plugin files"
        # 官方插件, 用覆盖的方式, 删掉所有目录, 默认情况下, 官方插件所有都在同一个包里.
        # 第三方插件, 删掉的是对应的插件目录.
        rm -rf ${BINDIR%/*}
    fi
fi

# 解压配置到目标路径
cd $TMP
echo "coming into: $TMP"

if [ "${CATEGORY}" == "EXTERNAL" -a -n "$GROUP_DIR" ]; then
    # 解压文件到临时目录 然后转移到对应目录 规避同台机器并发导致的部分实例目录为空问题
    # 第三方插件指定了instance_id，解压后需要将插件从标准路径移动到实例路径下
    echo "unzip ${PACKAGE} to dir: ${EXTERNAL_PLUGIN_TMPDIR}"
    tar xvf ${PACKAGE} -C ${EXTERNAL_PLUGIN_TMPDIR} || (echo "unzip ${PACKAGE} to ${EXTERNAL_PLUGIN_TMPDIR} failed!" && exit 1)
    mkdir -p $BINDIR
    mv $EXTERNAL_PLUGIN_TMPDIR/external_plugins/$PLUGIN_NAME/ $(dirname "$BINDIR") || (echo "mv $EXTERNAL_PLUGIN_TMPDIR/external_plugins/$PLUGIN_NAME/ to $(dirname "$BINDIR") failed." && exit 1)
else
    tar xvf $PACKAGE -C $GSE_HOME
fi

# 恢复配置文件
if [ "$RESERVE_CONF" == 1 ]; then
    echo "recover config file"
    tar xPf $(ls -rt $BACKUP_DIR/${PLUGIN_NAME}-*.pz | tail -1) $ETCDIR || exit 1
fi

# 输出看看更新后的信息. debug 时用.
#ls -l $BINDIR/$PLUGIN_NAME $ETCDIR/${PLUGIN_NAME}.conf
#cat $ETCDIR/${PLUGIN_NAME}.conf