#!/usr/bin/env python3
#-*- coding:utf-8 -*-  

############################
# Usage:
# File Name: urlmon.py
# Author: annhe  
# Mail: i@annhe.net
# Created Time: 2016-08-05 15:06:15
############################

import itopy
import json
import os
import configparser
import git
import datetime
import shutil

# 解析配置文件
config = configparser.ConfigParser()
config.read("conf.ini")   # 注意这里必须是绝对路径
 
itop_api=config.get("itop", "api")
itop_api_version=config.get("itop", "version")
itop_user=config.get("itop", "user")
itop_pwd=config.get("itop", "passwd")
# 执行频率
interval = int(config.get("itop", "interval")) * 60 + 5

tmp_dir = config.get("telegraf", "tmpdir")
telegraf_dir = config.get("telegraf", "gitdir")
telegraf_git = config.get("telegraf", "giturl")

itop = itopy.Api()
itop.connect(itop_api, itop_api_version, itop_user, itop_pwd)

now = datetime.datetime.now()
start = now- datetime.timedelta(seconds=interval)
start_str = start.strftime('%Y-%m-%d %H:%M:%S')

def getObjByTime(start):
	oql = 'SELECT CMDBChangeOp AS c WHERE c.objclass="Url" AND date>"' + start + '"'
	url = itop.get('CMDBChangeOp', oql)['objects']

	objkeys = []
	if url:
		for k,v in url.items():
			objkeys.append(v['fields']['objkey'])

	objkeys = "','".join(list(set(objkeys)))

	oql = "SELECT Url AS u WHERE u.id IN ('" + objkeys + "')"
	data = itop.get('Url', oql)['objects']
	return(data)

def getObjById(url_id):
	oql = 'SELECT Url AS u WHERE u.id = "' + url_id + '"'
	data = itop.get('Url', oql)['objects']
	return(data)

def writeConfFile(f, response_timeout = "15s", follow_redirects = "true", insecure_skip_verify = "true"):
	filedir = os.path.join(tmp_dir,f['monitor_node'])
	if not os.path.isdir(filedir):
		os.makedirs(filedir)

	filepath = os.path.join(tmp_dir, f['monitor_node'], f['applicationsolution_name'] + "_" + \
			f['url'].replace("://", "_").replace("/","_") + ".conf")

	headers = f['headers'].replace('\r\n', '\n').replace(': ', ':').split('\n')
	h = []
	for header in headers:
		h.append(header.replace(":", ' = "', 1) + '"')
	h_str = "\n\t\t".join(h)
	
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

def gitOps(tmp_dir=tmp_dir, telegraf_dir=telegraf_dir, telegraf_git=telegraf_git):
	if not os.path.isdir(telegraf_dir):
		repo = git.Repo.clone_from(telegraf_git, telegraf_dir)
	else:
		repo = git.Repo(telegraf_dir)
	g = repo.git

	dirs = os.listdir(tmp_dir)
	
	for d in dirs:
		monit_node = d
		if not os.path.isdir(os.path.join(telegraf_dir, monit_node)):
			os.mkdir(os.path.join(telegraf_dir, monit_node))

		try:
			g.checkout(monit_node)
		except:
			g.checkout(b=monit_node)
		
		commit = ""
		for item in os.listdir(os.path.join(tmp_dir, d)):
			dest = os.path.join(telegraf_dir, d)
			destfile = os.path.join(dest, item)
			if os.path.isfile(destfile):
				os.remove(destfile)
			shutil.move(os.path.join(tmp_dir, d, item), dest)
			commit = commit + d + "/" + item + "\n"
		
		g.add("--all")
		try:
			g.commit(m=commit)
		except:
			print(g.status())
		g.push("origin", monit_node)
	
def run(runtype="time",oid=None):
	if runtype == "time":
		data = getObjByTime(start_str)
	else:
		data = getObjById(oid)
	if data:
		for k,v in data.items():
			f = v['fields']
			writeConfFile(f)
	gitOps()

if __name__ == '__main__':
	run()
