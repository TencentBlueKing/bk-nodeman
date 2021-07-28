#!/bin/ksh

echo "Showing used ports"

echo "===== list of used ports begin ====="

netstat -Aan | awk '{print$5}'| grep -E "\*.[0-9]"

echo "===== list of used ports end ====="