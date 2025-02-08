#!/bin/bash

# 检查 jq 是否安装
if ! command -v jq &> /dev/null
then
    echo "jq 未安装，请先安装 jq 工具。"
    exit 1
fi

# 从 .proc 文件中过滤掉 procName 为 dbm_redis_exporter 的项
jq '.proc |= map(select(.procName != "dbm_redis_exporter"))' .proc > temp.proc

# 检查 jq 命令是否成功执行
if [ $? -eq 0 ]; then
    # 如果成功，将临时文件内容覆盖原文件
    mv temp.proc .proc
    echo "文件更新成功。"
else
    # 如果失败，删除临时文件并给出错误提示
    rm -f temp.proc
    echo "处理文件时发生错误。"
fi