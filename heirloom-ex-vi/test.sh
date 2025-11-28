#!/bin/bash
set -euo pipefail
./configure && make
TERM=xterm /root/dim/testty.py --run "./ex ex.h" --input "1,20p[enter]q[enter]" > /tmp/ex_test.txt
diff test.txt /tmp/ex_test.txt && echo "pass"
