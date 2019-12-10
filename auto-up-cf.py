#!/usr/bin/python3

import sys
import datetime
import dns.resolver
import json
import os
import CloudFlare

config_file = '.config'
dns_cache = '.dns-cache'
log_file = '/var/log/auto-up-cf.log'

def print_log(message):
	now = datetime.datetime.now().strftime("%c")

	try:
		fh = open(log_file, 'a')
		fh.write(now + " [auto-up-cf.py] " + message + "\n")
	except FileNotFoundError:
		pass

def main():
	domain = subdomain = record_type = live_record = live_record_id = cached_record = cached_record_id = zone_id = zone_name = None
	try:
		fh = open(config_file, 'r')
	except FileNotFoundError:
		print_log(config_file + " not found")
		sys.exit()

	for line in fh:
		if line.split("=")[0] == "domain":
			domain = line.split("=")[1].strip()
		if line.split("=")[0] == "subdomain":
			subdomain = line.split("=")[1].strip()
		if line.split("=")[0] == "record_type":
			record_type = line.split("=")[1].strip()

	if domain is None:
		print_log("domain is not defined")
		sys.exit()
	if record_type is None:
		print_log("record_type is not defined")
		sys.exit()

	if os.path.exists(dns_cache):
		try:
			with open(dns_cache) as json_file:
				cached_data = json.load(json_file)
				cached_domain = cached_data['domain']
				cached_record = cached_data['live_record']
				cached_record_id = cached_data['live_record_id']
		except Exception as e:
			print("got %s on json.load()" % e)

	if cached_record is not None and cached_record_id is not None:
		log_entry = "found cached results: " + cached_record + " " + cached_record_id
		print_log(log_entry)

	resolv = dns.resolver.Resolver()
	resolver_data = resolv.query('resolver1.opendns.com', 'A')
	for rdata in resolver_data:
		resolver_ip = rdata
	resolv.nameservers = [str(resolver_ip)]

	try:
		answer = resolv.query('myip.opendns.com', 'A')
		for rdata in answer:
			server_ip = str(rdata)
	except:
		print_log("couldn't obtain IP address")
		sys.exit()

	if cached_record == server_ip:
		print_log("server IP matches cache")
		sys.exit()

	cf = CloudFlare.CloudFlare()
	zones = cf.zones.get()
	for zone in zones:
		if domain == zone['name']:
			zone_id = zone['id']
			zone_name = zone['name']
			break
	try:
		dns_records = cf.zones.dns_records.get(zone_id)
	except CloudFlare.exceptions.CloudFlareAPIError as e:
		exit('/zones/dns_records.get %d %s - api call failed' % (e, e))

	if subdomain is not None:
		domain = subdomain + "." + domain

	for dns_record in dns_records:
		if dns_record['name'] == domain and dns_record['type'] == "A":
			live_record = dns_record['content']
			live_record_id = dns_record['id']
			break

	if live_record is not None and server_ip != cached_record:
		try:
			with open(dns_cache, 'w') as fh:
				cached_results = {}
				cached_results['domain'] = domain
				cached_results['live_record'] = live_record
				cached_results['live_record_id'] = live_record_id
				json.dump(cached_results, fh)
		except FileNotFoundError:
			print_log(dns_cache + " not found")
			sys.exit()

		log_entry = "cached CF response: " + live_record + " " + live_record_id
		print_log(log_entry)

	new_dns_record = {'name':domain, 'type':record_type, 'content':server_ip}

	if live_record != server_ip:
		if live_record_id is not None:
			try:
				cf.zones.dns_records.put(zone_id,live_record_id,data=new_dns_record)
			except CloudFlare.exceptions.CloudFlareAPIError as e:
				exit('/zones.dns_records.post %s %s - %d %s' % (zone_name, new_dns_record['name'], e, e))
				sys.exit()
			print_log("Updated " + domain + " to " + server_ip)
		else:
			try:
				cf.zones.dns_records.post(zone_id,data=new_dns_record)
			except CloudFlare.exceptions.CloudFlareAPIError as e:
				exit('/zones.dns_records.post %s %s - %d %s' % (zone_name, new_dns_record['name'], e, e))
				sys.exit()
			print_log("Created " + record_type + " record for " + domain + " with contents: " + server_ip)
	else:
		print_log("live record and server IP match")

if __name__ == '__main__':
	main()
