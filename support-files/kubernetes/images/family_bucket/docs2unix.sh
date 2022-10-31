#!/bin/bash

# 替换 .bat 文件的换行符

bat_filepaths=$(find "$1" -type f -name "*.bat")

while read -r bat_filepath
do
  awk 'sub("$","\r")' "${bat_filepath}" > "${bat_filepath}_w" && mv -f "${bat_filepath}_w" "${bat_filepath}"
done <<< "$bat_filepaths"
