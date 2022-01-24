#!/bin/ksh

echo "clean debug plugin"


while getopts n:p:g: arg; do
    case $arg in
        n)  export PLUGIN_NAME=${OPTARG} ;;
        p)  export INSTALL_PATH=${OPTARG} ;;
        g)  export GROUP_ID=${OPTARG} ;;
        *)  usage ;;
    esac
done

if [[ $GROUP_ID == "" ]];then
    echo "group id can not be empty!"
    exit 1
fi

export BINDIR=$INSTALL_PATH/external_plugins/$GROUP_ID/$PLUGIN_NAME/

echo "Stopping debug process..."

for file in $BINDIR/pid/*
do
    if test -f $file
    then
        pid=`cat $file`
        echo "Found PID file: $file"
        echo "PID to be killed: $pid"
        kill $pid
    fi
done

echo "Removing plugin directory..."

rm -rf $plugin_install_path

exit 0