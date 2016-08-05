#!/usr/bin/env python3
#-*- coding:utf-8 -*-  

############################
# Usage:
# File Name: test.py
# Author: annhe  
# Mail: i@annhe.net
# Created Time: 2016-08-04 19:45:48
############################

import itopy
import json
import os
import configparser
import git
import datetime

# 解析配置文件
config = configparser.ConfigParser()
config.read("conf.ini")   # 注意这里必须是绝对路径
 
itop_api=config.get("itop", "api")
itop_api_version=config.get("itop", "version")
itop_user=config.get("itop", "user")
itop_pwd=config.get("itop", "passwd")
# 执行频率
interval = int(config.get("itop", "interval"))

telegraf_dir = config.get("telegraf", "gitdir")
telegraf_git = config.get("telegraf", "giturl")

itop = itopy.Api()
itop.connect(itop_api, itop_api_version, itop_user, itop_pwd)

now = datetime.datetime.now() - datetime.timedelta(minutes=interval)
print(now.strftime('%Y-%m-%d %H:%M:%S'))

#SELECT CMDBChangeOp WHERE objclass="ApplicationSolution" AND date>"2016-07-25 22:49:16" AND finalclass != "CMDBChangeOpSetAttributeLinksAddRemove"
url = itop.get('CMDBChangeOp', 'SELECT CMDBChangeOp AS c WHERE c.objclass="Url" AND date>"2016-08-04 20:20:00"')['objects']

objkeys = []
if url:
	for k,v in url.items():
		objkeys.append(v['fields']['objkey'])

objkeys = "','".join(list(set(objkeys)))

oql = "SELECT Url AS u WHERE u.id IN ('" + objkeys + "')"
data = itop.get('Url', oql)['objects']

if data:
	for k,v in data.items():
		f = v['fields']
		response_timeout = "15s"
		follow_redirects = "true"
		insecure_skip_verify = "true"
		monit_node = f['monitor_node']
		headers = f['headers'].replace('\r\n', '\n').replace(': ', ':').split('\n')
		h = []
		for header in headers:
			h.append(header.replace(":", ' = "', 1) + '"')

		h_str = "\n\t\t".join(h)
		print(h_str)
		if not os.path.isdir(telegraf_dir):
			repo = git.Repo.clone_from(telegraf_git, telegraf_dir)
		else:
			repo = git.Repo(telegraf_dir)

		git = repo.git
		if not os.path.isdir(telegraf_dir + "/" + monit_node):
			os.mkdir(telegraf_dir + "/" + monit_node)

		try:
			git.checkout(monit_node)
		except:
			git.checkout(b=monit_node)
			
		#git.checkout("HEAD", b=monit_node)

		filename = monit_node + "/" + f['applicationsolution_name'] + "_" + \
				f['url'].replace("://", "_").replace("/","_") + ".conf"
		filepath = telegraf_dir + "/" + filename
		print(filename)
		with open(filepath, 'w') as fi:
			fi.write("[[inputs.url_monitor]]\n" + \
					"\tapp = " + '"' +  f['applicationsolution_name'] + '"\n' + \
					"\taddress = " + '"' + f['url'] + '"\n' + \
					"\tresponse_timeout = \"" + response_timeout + '"\n' + \
					"\tmethod = " + '"' + f['method'] + '"\n' + \
					"\trequire_str = " + "'" + f['require_str'] + "'\n" + \
					"\trequire_code = " + "'" + f['require_code'] + "'\n" + \
					"\tfailed_count = " + f['failed_count'] + '\n' + \
					"\tfailed_timeout = " + f['timeout'] + '\n' + \
					"\tfollow_redirects = " + follow_redirects + '\n' + \
					"\tbody = " + "'" + f['body'] + "'\n" + \
					"\tinsecure_skip_verify = " + insecure_skip_verify + '\n' + \
					"\t[inputs.url_monitor.headers]\n\t\t" + h_str + '\n')

		git.add(filename)
		try:
			git.commit(m=filename)
		except:
			print(git.status())
		git.push("origin", monit_node)
