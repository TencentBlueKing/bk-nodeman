#!/bin/sh

usage () {
    echo "usage: operate_plugin OPTIONS"
    echo "OPTIONS"
    echo "  -t  plugin category, could be: official/external/scripts"
    echo "  -n  plugin name"
    echo "  -p  home path of plugin"
    echo "  -c  command to run"
    echo "  -g  group id"
    exit 0
}

guess_target_dir () {
    case $CATEGORY in
        official | 1)
            export BINDIR=$INSTALL_PATH/plugins/bin
            ;;
        external | 2)
            export BINDIR=$INSTALL_PATH/external_plugins/$GROUP_ID/$PLUGIN_NAME/
            ;;
        scripts | 3)
            export BINDIR=$INSTALL_PATH/external_scripts/
            ;;
        *)
            echo "unkown category. abort"
            exit 1
            ;;
    esac
}


while getopts t:n:p:c:g: arg; do
    case $arg in
        t)  export CATEGORY=$OPTARG ;;
        n)  export PLUGIN_NAME=${OPTARG} ;;
        p)  export INSTALL_PATH=${OPTARG} ;;
        c)  export RUN_CMD=${OPTARG} ;;
        g)  export GROUP_ID=${OPTARG} ;;
        *)  usage ;;
    esac
done

guess_target_dir

cd ${BINDIR}
${RUN_CMD}
