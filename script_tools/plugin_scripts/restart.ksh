#!/bin/ksh

usage () {
    echo "usage: $0 PLUGIN_NAME"
    echo "/usr/local/gse/plugins/bin/restart.sh aixbeat"
    exit 0
}

cd $(dirname $0) 2>/dev/null
[ -z "$1" ] && usage
./stop.ksh $@ >/dev/null 2>&1 && ./start.ksh $@ >/dev/null 2>&1
