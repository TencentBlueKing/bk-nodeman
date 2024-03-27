#!/bin/sh

echo "Showing used ports"

echo "===== list of used ports begin ====="

netstat -lntup | awk '{print $4}'

echo "===== list of used ports end ====="
