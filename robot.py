#!/usr/bin/env python3
#-*- coding:utf-8 -*-  

############################
# Usage: 用于将工单生成csv格式
# File Name: robot.py
# Author: annhe  
# Mail: i@annhe.net
# Created Time: 2016-08-05 15:06:15
############################

from libs import itopy
import json
import os
import configparser
import datetime
import sys

# 解析配置文件
path = os.path.dirname(os.path.abspath(__file__))
config = configparser.ConfigParser()
config.read(os.path.join(path, "conf.ini"))   # 注意这里必须是绝对路径
 
itop_api=config.get("itop", "api")
itop_api_version=config.get("itop", "version")
itop_user=config.get("itop", "user")
itop_pwd=config.get("itop", "passwd")

itop = itopy.Api()
itop.connect(itop_api, itop_api_version, itop_user, itop_pwd)

# 解析地址对应表
def getResolve(cluster):
	try:
		re = config.get("resolve", cluster)
		return(re)
	except:
		return("unknown")

# 判断工单是否已经处理过
def isDealed(item):
	flag = False
	done = ""
	public_log = item['fields']['public_log']['entries']
	for log in public_log:
		if log['user_login'] == 'ticket_robot':
			done = "[" + item['fields']['ref'] + "]" + item['fields']['title'] + ": 此工单已处理过\n"
			flag = True
			continue
	return(flag,done)

# ticket_robot标记public_log 
def ticketDone(objkey, public_log="robot done"):
	error = ""
	robot_ret = itop.update('UserRequest', objkey, public_log="robot done")
	if robot_ret['code'] != 0:
		error = item['fields']['ref'] + ": robot更新失败\n"
	return(error)

# write csv file
def writeCsv(filename,csv):
	with open(filename, 'w') as f:
		f.write(csv)

# 处理数据库工单
def dealDatabase(data, force=False):
	label = "名称,类型(mysql/mongo),业务描述,QPS预估(如2000),读写比例预估(如8|2),数据容量及增长,地区(例如香港),接收人邮箱前缀(#分隔),缓存(cbase/redis/无缓存),备注\n"
	lines = ""
	done = ""
	errors = ""
	filename = "database"

	if not data:
		return(filename,done,errors)
	for k,item in data.items():
		# 只处理数据库申请工单
		if item['fields']['servicesubcategory_name'] != "MongoDB申请":
			continue
		else:
			database_type = "mongo"
		
		# 判断工单是否已经处理过
		dealstatus = isDealed(item)
		#print(dealstatus)
		if dealstatus[0] and force == False:
			continue
		done += dealstatus[1]

		objkey = item['key']
		filename += "_" + objkey
		public_log = item['fields']['public_log']['entries']
		info = public_log[0]['message']
		contact = item['fields']['contacts_list'][0]['contact_email'].split('@')[0]
		oDict = {}
		for i in info.split("\n"):
			tmp = i.split(" : ")
			oDict[tmp[0]] = tmp[1]

		errors += ticketDone(objkey)

		lines += oDict['名称'] + "," + database_type + "," + oDict['所属APP'] + "," + oDict['QPS预估'] + \
		"," + oDict['读写比例预估'] + "," + oDict['数据容量及增长'] + "," + oDict['地区'] + \
		"," + contact + "," + oDict['缓存类型'] + "\n"

	csv = label + lines
	filename += ".csv"
	writeCsv(filename, csv)
	return(filename,done,errors)

# 处理域名工单
def dealDomain(data, force=False):
	label = "域名,变更类型(新增/变更),业务描述,智能解析(是/否),默认解析地址,电信(非智能解析留空),联通(非智能解析留空),接收人邮箱前缀(#分隔)\n"
	lines = ""
	done = ""
	errors = ""
	filename = "domain"

	if not data:
		return(filename,done,errors)

	for k,item in data.items():
		# 只处理域名工单
		if item['fields']['servicesubcategory_name'] != "域名申请":
			continue
		
		# 判断工单是否已经处理过
		dealstatus = isDealed(item)
		if dealstatus[0] and force == False:
			continue
		done += dealstatus[1]

		objkey = item['key']
		filename += "_" + objkey
		public_log = item['fields']['public_log']['entries']
		info = public_log[0]['message']
		contact = item['fields']['contacts_list'][0]['contact_email'].split('@')[0]
		oDict = {}
		for i in info.split("\n"):
			tmp = i.split(" : ")
			if tmp[0] == "解析地址":
				tmp[1] = getResolve(tmp[1])
			try:
				oDict[tmp[0]] = tmp[1]
			except:
				pass

		errors += ticketDone(objkey)

		lines += oDict['域名'] + ",新增," + oDict['所属APP'] + ",否," + oDict['解析地址'] + ",,," + contact + "\n"

	csv = label + lines
	filename += ".csv"
	writeCsv(filename, csv)
	return(filename,done,errors)

def getObjById(r_id,force=False):
	oql = 'SELECT UserRequest AS r WHERE r.id = "' + r_id + '" AND r.status="assigned"'
	data = itop.get('UserRequest', oql)['objects']
	domain_data = dealDomain(data,force)
	db_data = dealDatabase(data,force)
	return(domain_data + db_data)
		
def getAllAssignedTicket(force=False):
	oql = 'SELECT UserRequest AS r WHERE r.status="assigned"'
	data = itop.get('UserRequest', oql)['objects']
	domain_data = dealDomain(data,force)
	db_data = dealDatabase(data,force)
	
	return(domain_data + db_data)

def run(runtype="all", oid="", force=False):
	if runtype == "id":
		ret = getObjById(oid,force)
	elif runtype == "all":
		ret = getAllAssignedTicket(force)
	print(ret)
	#print("csv文件名: \n" + ret[0])
	#print("\n已处理工单列表: \n" + ret[1])

if __name__ == '__main__':
	if sys.argv[1] == "all":
		try:
			if sys.argv[2] == "-f":
				run(sys.argv[1],force=True)
		except:
			run(sys.argv[1])
	else:
		try:
			if sys.argv[2] == "-f":
				run("id", sys.argv[1], force=True)
		except:
			run("id", sys.argv[1])
