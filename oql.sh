#!/bin/bash

############################
# Usage:
# File Name: oql.sh
# Author: annhe  
# Mail: i@annhe.net
# Created Time: 2016-06-12 10:43:14
############################
[ $# -lt 1 ] && echo $0 file && exit 1
file=$1

ip2server="SELECT Server AS s JOIN PhysicalIP AS ip ON ip.connectableci_id=s.id WHERE ip.ipaddress IN"
hostname="SELECT Server AS s WHERE s.hostname IN"
app="SELECT ApplicationSolution AS app WHERE app.name IN" 
cilist=`cat $file |sort -u |tr '\n' ',' |tr -d ' '| sed "s/,/','/g" |sed -r "s/^/'/g" |sed "s/'$//g" |sed "s/,$//g"`


case $2 in
	server) echo "$ip2server ($cilist)";;
	host) echo "$hostname ($cilist)";;
	app) echo "$app ($cilist)";;
	*) echo "nothing to do";;
esac

