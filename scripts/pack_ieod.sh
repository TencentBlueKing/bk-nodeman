#!/bin/sh
SCRIPT_DIR=`dirname $0`

cd $SCRIPT_DIR && cd .. || exit 1

sed -i '/static\/nodeman/d' .gitignore

# 调整requirements
sed -ie 's/blueapps-open/blueapps/g' requirements.txt
echo -e '
blueking-component-ieod==0.1.12
bkoauth==0.0.22
' >> requirements.txt

# 删除blueking，因为内置的blueking, bkoauth只有open版
rm -rf blueking
rm -rf bkoauth