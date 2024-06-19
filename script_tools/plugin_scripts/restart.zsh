#!/bin/bash

cd ${BASH_SOURCE%/*} 2>/dev/null
./stop.zsh $@ >/dev/null && ./start.zsh $@ >/dev/null
