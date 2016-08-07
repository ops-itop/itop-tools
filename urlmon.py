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
import sys
import glob

# 解析配置文件
path = os.path.dirname(os.path.abspath(__file__))
config = configparser.ConfigParser()
config.read(os.path.join(path, "conf.ini"))   # 注意这里必须是绝对路径
 
itop_api=config.get("itop", "api")
itop_api_version=config.get("itop", "version")
itop_user=config.get("itop", "user")
itop_pwd=config.get("itop", "passwd")
# 执行频率
interval = int(config.get("itop", "interval")) * 60 + 5

tmp_dir = os.path.join(path, config.get("telegraf", "tmpdir"))
telegraf_dir = os.path.join(path, config.get("telegraf", "gitdir"))
telegraf_git = config.get("telegraf", "giturl")

itop = itopy.Api()
itop.connect(itop_api, itop_api_version, itop_user, itop_pwd)

now = datetime.datetime.now()
start = now- datetime.timedelta(seconds=interval)
start_str = start.strftime('%Y-%m-%d %H:%M:%S')

if not os.path.isdir(tmp_dir):
	os.mkdir(tmp_dir)

def getDeleted(start_str):
	del_oql = 'SELECT CMDBChangeOpDelete AS c WHERE c.objclass="FunctionalCI" AND c.date > "' + start_str + '"'
	dels = itop.get('CMDBChangeOpDelete', del_oql)
	try:
		deleted = dels['objects']
	except:
		print(dels)
	
	objkeys = []
	if deleted:
		for k,v in deleted.items():
			objkeys.append(v['fields']['objkey'])

	mod_oql = 'SELECT CMDBChangeOpSetAttributeScalar AS c WHERE c.objclass="Url" AND c.attcode="monitor_node" ' + \
			'AND date > "' + start_str + '"'
	mods = itop.get('CMDBChangeOpSetAttributeScalar', mod_oql)
	try:
		modified = mods['objects']
	except:
		print(mods)

	if modified:
		for k,v in modified.items():
			objkeys.append(v['fields']['objkey'])

	return(objkeys)

def getObjByTime(start_str):
	oql = 'SELECT CMDBChangeOp AS c WHERE c.objclass="Url" AND c.date>"' + start_str + '"'
	url_obj = itop.get('CMDBChangeOp', oql)
	try:
		url = url_obj['objects']
	except:
		print(url_obj)
		sys.exit()

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

	filepath = os.path.join(tmp_dir, f['monitor_node'], f['id'] + ".conf")

	headers = f['headers'].replace('\r\n', '\n').replace(': ', ':').split('\n')
	h = []
	for header in headers:
		if header != "":
			h.append(header.replace(":", ' = "', 1) + '"')
	h_str = "\n\t\t".join(h)
	
	timeout = f['timeout']
	if timeout == "":
		timeout = "1"
	
	if f['interval'] == "":
		f['interval'] = "30"
	if f['failed_count'] == "":
		f['failed_count'] = "3"
	
	with open(filepath, 'w') as fi:
		fi.write("[[inputs.url_monitor]]\n" + \
				"\tapp = " + '"' +  f['applicationsolution_name'] + '"\n' + \
				"\taddress = " + '"' + f['url'] + '"\n' + \
				"\tinterval = " + '"' + f['interval'] + 's"\n' + \
				"\tresponse_timeout = \"" + response_timeout + '"\n' + \
				"\tmethod = " + '"' + f['method'] + '"\n' + \
				"\trequire_str = " + "'" + f['require_str'] + "'\n" + \
				"\trequire_code = " + "'" + f['require_code'] + "'\n" + \
				"\tfailed_count = " + f['failed_count'] + '\n' + \
				"\tfailed_timeout = " + str("%.2f" % float(timeout)) + '\n' + \
				"\tfollow_redirects = " + follow_redirects + '\n' + \
				"\tbody = " + "'" + f['body'] + "'\n" + \
				"\tinsecure_skip_verify = " + insecure_skip_verify + '\n' + \
				"\t[inputs.url_monitor.headers]\n\t\t" + h_str + '\n')

# 删除已被删除的Url或者修改了monitor_node的Url配置
def delConf(delobj=[], telegraf_dir=telegraf_dir):
	nodes = os.listdir(telegraf_dir)
	if ".git" in nodes:
		nodes.remove(".git")

	commit = ""
	for node in nodes:
		for obj in delobj:
			#print(obj)
			delfile = glob.glob(os.path.join(telegraf_dir, node, obj + ".*"))
			if delfile:
				os.remove(delfile[0])
				commit = "delete " + delfile[0] + "\n"
			#print(delfile)
	return(commit)

def gitOps(delobj=[], tmp_dir=tmp_dir, telegraf_dir=telegraf_dir, telegraf_git=telegraf_git):
	if not os.path.isdir(telegraf_dir):
		repo = git.Repo.clone_from(telegraf_git, telegraf_dir)
	else:
		repo = git.Repo(telegraf_dir)
	g = repo.git
	try:
		g.pull("origin", "master")
	except:
		print("pull faild")

	
	commit = ""
	commit = commit + delConf(delobj, telegraf_dir)

	dirs = os.listdir(tmp_dir)
	
	for d in dirs:
		monit_node = d
		if not os.path.isdir(os.path.join(telegraf_dir, monit_node)):
			os.mkdir(os.path.join(telegraf_dir, monit_node))

		for item in os.listdir(os.path.join(tmp_dir, d)):
			dest = os.path.join(telegraf_dir, d)
			destfile = os.path.join(dest, item)
			if os.path.isfile(destfile):
				os.remove(destfile)
			shutil.move(os.path.join(tmp_dir, d, item), dest)
			print(os.path.join(tmp_dir, d, item) + " -- " + dest)
			commit = commit + "update " + d + "/" + item + "\n"
		
	g.add("--all")
	try:
		g.commit(m=commit)
		g.push("origin", "master")
	except:
		print(g.status())
	
def run(runtype="time",oid=""):
	delobj = []
	if runtype == "time":
		if oid != "":
			data = getObjByTime(oid)
			delobj = getDeleted(oid)
		else:
			data = getObjByTime(start_str)
			delobj = getDeleted(start_str)
	else:
		data = getObjById(oid)
	if data:
		for k,v in data.items():
			f = v['fields']
			f['id'] = v['key']
			writeConfFile(f)
	gitOps(delobj)

if __name__ == '__main__':
	if len(sys.argv) < 2:
		run()
	elif sys.argv[1] == "time":
		run("time", sys.argv[2])
	else:
		run("id", sys.argv[1])
