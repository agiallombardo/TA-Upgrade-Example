#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: Apache-2.0

. `dirname $0`/common.sh

HEADER='NAME                                                     VERSION               RELEASE               ARCH        VENDOR                          GROUP'
HEADERIZE="BEGIN {print \"$HEADER\"}"
PRINTF='{printf "%-55.55s  %-20.20s  %-20.20s  %-10.10s  %-30.30s  %-20s\n", name, version, release, arch, vendor, group}'

CMD='echo There is no flavor-independent command...'
if [ "x$KERNEL" = "xLinux" ] ; then
	if $DEBIAN; then
		CMD1="eval dpkg-query -W -f='"
		CMD2='${Package}  ${Version}  ${Architecture}  ${Homepage}\n'
		CMD3="'"
		CMD=$CMD1$CMD2$CMD3
		FORMAT='{name=$1;version=$2;sub("\.?[^0-9\.:\-].*$", "", version); release=$2; sub("^[0-9\.:\-]*","",release); if(release=="") {release="?"}; arch=$3; if (NF>3) {sub("^.*:\/\/", "", $4); sub("^www\.", "", $4); sub("\/.*$", "", $4); vendor=$4} else {vendor="?"} group="?"}'
	else
		CMD='eval rpm --query --all --queryformat "%-56{name}  %-21{version}  %-21{release}  %-11{arch}  %-31{vendor}  %-{group}\n"'
		PRINTF='{print $0}'
	fi
elif [ "x$KERNEL" = "xSunOS" ] ; then
	CMD='pkginfo -l'
	FORMAT='/PKGINST:/ {name=$2 ":"} /NAME:/ {for (i=2;i<=NF;i++) name = name " " $i} /CATEGORY:/ {group=$2} /ARCH:/ {arch=$2} /VERSION:/ {split($2,a,",REV="); version=a[1]; release=a[2]} /VENDOR:/ {vendor=$2; for(i=3;i<=NF;i++) vendor = vendor " " $i}'
	SEPARATE_RECORDS='!/^$/ {next} {release = release ? release : "?"}'
elif [ "x$KERNEL" = "xAIX" ] ; then
	CMD='eval lslpp -icq | sed "s,:, ," | sed "s,:.*,,"'
	FORMAT='{name=$2 ; version=$3 ; vendor=release=arch=group="?"}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
	CMD='system_profiler SPApplicationsDataType'
	FILTER='{ if (NR<3) next}'
	FORMAT='{gsub("[^\40-\176]", "", $0)} /:$/ {sub("^[ ]*", "", $0); sub(":$", "", $0); name=$0} /Last Modified: / {vendor=""} /Version: / {version=$2} /Kind: / {arch=$2} /Get Info String: / {sub("^.*: ", "", $0); sub("[Aa]ll [Rr]ights.*$", "", $0); sub("^.*[Cc]opyright", "", $0); sub("^[^a-zA-Z_]*[0-9][0-9[0-9][0-9]", "", $0); sub("^[ ]*", "", $0); vendor=$0}'
	SEPARATE_RECORDS='!/Location:/ {next} {release = "?"; vendor = vendor ? vendor : "?"; group = "?"}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand swlist
    CMD='swlist -a revision -a architecture -a vendor_tag'
    FILTER='/^#/ {next} $1=="" {next}'
    FORMAT='{release="?"; group="?"; vendor="?"; name=$1; version=$2; arch=$3} NF==4 {vendor=$4}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	# the below syntax is valid when using zsh, bash, ksh
	if [[ $KERNEL_RELEASE =~ 10.* ]] || [[ $KERNEL_RELEASE =~ 11.* ]] || [[ $KERNEL_RELEASE =~ 12.* ]] || [[ $KERNEL_RELEASE =~ 13.* ]]; then
		CMD='eval pkg info --raw --all | grep "^name:\|^version:\|^arch:" | cut -d\" -f2'
		HEADER='NAME                                               VERSION                                            ARCH        '
		HEADERIZE="BEGIN {print \"$HEADER\"}"
		PRINTF='{ printf "%-50.50s" (NR%3==0 ? RS:FS),$1}'
	else
		CMD='pkg_info -da'
		FORMAT='/^Information for / {vendor=""; sub(":$", "", $3); name=$3} /^WWW: / {sub("^.*//", "", $2); sub("/.*$", "", $2); sub("^www\134.", "", $2); vendor=$2} /^$/ {blanks+=1} !/^$/ {blanks=0}'
		SEPARATE_RECORDS='(blanks<3) {next} {vendor = vendor ? vendor : "?"; version=release=arch=group="?"}'
	fi
fi

assertHaveCommand $CMD
$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILTER $FORMAT $SEPARATE_RECORDS $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILTER $FORMAT $SEPARATE_RECORDS $PRINTF' header=\"$HEADER\"" >> $TEE_DEST