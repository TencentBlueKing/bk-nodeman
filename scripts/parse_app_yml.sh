#!/bin/sh

# 设置前缀
prefix=$2
s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
result=$(sed -ne "s|^\($s\)\($w\)$s:$s\"\(.*\)\"$s\$|\1$fs\2$fs\3|p" \
    -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
awk -F$fs '{
  indent = length($1)/2;
  vname[indent] = $2;
  for (i in vname) {if (i > indent) {delete vname[i]}}
  if (length($3) > 0) {
     vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
     printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
  }
}')

echo ${result}
# 赋值到环境变量中
eval ${result}
# 下一个版本号
yml_next_version=$(echo ${yml_version} | awk -F. -v OFS=. 'NF==1{print ++$NF}; NF>1{if(length($NF+1)>length($NF))$(NF-1)++; $NF=sprintf("%0*d", length($NF), ($NF+1)%(10^length($NF))); print}')
echo yml_next_version=${yml_next_version}
