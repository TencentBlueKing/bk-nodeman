#!/bin/bash

WORKSPACE=$1
RELEASE_VERSION=$2
RELEASE_ENV=$3


if [ "${RELEASE_ENV}" == "ee" ]; then
    RUN_VER="open"
else
    RUN_VER="ieod"
fi

echo "WORKSPACE: ${WORKSPACE}"
echo "RELEASE_VERSION: ${RELEASE_VERSION}"
echo "RELEASE_ENV: ${RELEASE_ENV}"

CODE_DIST_DIR="dist/bknodeman"
NODEMAN_DIST_DIR=${CODE_DIST_DIR}/nodeman

cd ${WORKSPACE}

echo "remove old dist dir"
# 删除之前的打包目录
rm -rf dist

mkdir -p ${CODE_DIST_DIR}/nodeman/
mkdir -p ${NODEMAN_DIST_DIR}/sites/${RUN_VER}
mkdir -p ${NODEMAN_DIST_DIR}/release
mkdir -p ${NODEMAN_DIST_DIR}/version_logs_html

# 0. 拷贝代码文件
echo "copy source code files"
python bk_nodeman/sites/change_run_ver.py -V ${RUN_VER}

cp -R bk_nodeman/apps ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/official_plugin ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/bin ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/bkoauth ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/blueapps ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/blueking ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/common ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/locale ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/pipeline ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/version_log ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/sites/${RUN_VER} ${NODEMAN_DIST_DIR}/sites
cp -R bk_nodeman/script_tools ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/config ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/iam ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/upgrade ${NODEMAN_DIST_DIR}
cp -R bk_nodeman/env ${NODEMAN_DIST_DIR}

cp bk_nodeman/manage.py ${NODEMAN_DIST_DIR}
cp bk_nodeman/settings.py ${NODEMAN_DIST_DIR}
cp bk_nodeman/app.yml ${NODEMAN_DIST_DIR}
cp bk_nodeman/urls.py ${NODEMAN_DIST_DIR}
cp bk_nodeman/wsgi.py ${NODEMAN_DIST_DIR}
cp bk_nodeman/on_migrate ${NODEMAN_DIST_DIR}
cp bk_nodeman/ignorefile ${CODE_DIST_DIR}

# 1. 替换bat的换行符
bat_filepaths=$(find ${NODEMAN_DIST_DIR}/script_tools -type f -name "*.bat")
while read -r bat_filepath
do
  awk 'sub("$","\r")' "${bat_filepath}" > "${bat_filepath}_w" && mv -f "${bat_filepath}_w" "${bat_filepath}"
done <<< "$bat_filepaths"


# 2. 企业版打包暂时不支持requirements.txt -r 的方式
sed -e '/requirements/d' bk_nodeman/requirements.txt > target.txt
if [ -e "requirements_env.txt" ]
then
  sed -e '/utf-8/d' bk_nodeman/requirements_env.txt >> target.txt
fi
mv target.txt bk_nodeman/requirements.txt

cp bk_nodeman/requirements.txt ${NODEMAN_DIST_DIR}

mkdir -p ${NODEMAN_DIST_DIR}/config
cp bk_nodeman/config/__init__.py ${NODEMAN_DIST_DIR}/config


find ${CODE_DIST_DIR} -name "*.pyc" -delete

# 3. 写入版本号
echo "create file: VERSION"
echo ${RELEASE_VERSION} > ${NODEMAN_DIST_DIR}/VERSION
echo ${RELEASE_VERSION} > ${CODE_DIST_DIR}/VERSION

# 4. 写入 project.yaml
echo "create file: project.yaml"
cat > ${CODE_DIST_DIR}/projects.yaml << EOF
- name: nodeman
  module: bknodeman
  project_dir: bknodeman/nodeman
  alias: nodeman
  version_type: ee
  language: python/3.6
  version: ${RELEASE_VERSION}
EOF

# 5. 拷贝support-files
echo "copy support-files dir"
cp -R bk_nodeman/support-files ${CODE_DIST_DIR}

# 6. 打压缩包
echo "zip package"
cd dist
tar -cvzf bknodeman_${RELEASE_ENV}-${RELEASE_VERSION}.tgz bknodeman

echo "make package done"
