#!/bin/bash

############################
# Usage:
# File Name: init-telegraf-url.sh
# Author: annhe  
# Mail: i@annhe.net
# Created Time: 2016-08-06 13:42:30
############################

conf="conf.ini"
basedir=$(cd `dirname $0`; pwd)
cd $basedir
interval=`grep "interval" $conf |awk '{print $NF}'`

sed -i "/urlmon\.py/d" /etc/crontab
sed -i "/telegraf-url-monitor/d" /etc/crontab

cat >>/etc/crontab<<EOF

# telegraf-url-monitor 定时抓取cmdb中url类的修改，提交到git
*/$interval * * * * root $basedir/urlmon.py &> $basedir/cron.urlmon.log
EOF

