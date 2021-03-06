#!/bin/sh
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: Apache-2.0

. `dirname $0`/common.sh

HEADER='USER               PID   PSR   pctCPU       CPUTIME  pctMEM     RSZ_KB     VSZ_KB   TTY      S       ELAPSED  COMMAND             ARGS'
FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^[^\134[: -]*/", "", $12)}'
PRINTF='{if (NR == 1) {print $0} else {printf "%32.32s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-100.100s  %s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, args}}'

HEADERIZE='{NR == 1 && $0 = header}'
CMD='ps auxww'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand ps
	CMD='ps -wweo uname:32,pid,psr,pcpu,cputime,pmem,rsz,vsz,tty,s,etime,args'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	assertHaveCommandGivenPath /usr/bin/ps
	CMD='/usr/bin/ps -eo user,pid,psr,pcpu,time,pmem,rss,vsz,tty,s,etime,args'
elif [ "x$KERNEL" = "xAIX" ] ; then
	assertHaveCommandGivenPath /usr/sysv/bin/ps
	CMD='/usr/sysv/bin/ps -eo user,pid,psr,pcpu,time,pmem,rss,vsz,tty,s,etime,args'
	FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^.*/|:|-", "", $12)}'
	# replace the tail ( ; sub("^[^\134[: -]*/", "", $12)}' ) of above can't be run
elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand ps
	CMD='ps axo ruser,pid,pcpu,cputime,pmem,rss,vsz,tty,state,etime,command'
	FILL_BLANKS='{if (NR>1) {for (i=NF; i>2; i--) $(i+1) = $i; $3 = "?"}}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand ps
    export UNIX95=1
    CMD='ps -e -o ruser,pid,pset,pcpu,time,vsz,tty,state,etime,args'
    FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^[\[\]]", "", $11)}'
    PRINTF='{if (NR == 1) {print $0} else {printf "%-14.14s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-18.18s  %s\n", $1, $2, $3, $4, $5, "?", "?", $6, $7, $8, $9, $10, $11, arg}}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	assertHaveCommand ps
	CMD='ps axo ruser,pid,pcpu,cputime,pmem,rss,vsz,tty,state,etime,command'
	FILL_BLANKS='{if (NR>1) {for (i=NF; i>2; i--) $(i+1) = $i; $3 = "?"}}'
	# the below condition is added for freenas support
	if [ `uname -i` = "FREENAS64" ] ; then
		FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^[\[\w\-\.\/\]+]*", "", $12)}'
		PRINTF='{if (NR == 1) {print $0} else {printf "%-32.32s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-100.100s  %s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, args}}'
	fi
fi

$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILL_BLANKS $FORMAT $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILL_BLANKS $FORMAT $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
