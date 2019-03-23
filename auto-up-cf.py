#!/usr/bin/python3

import sys
import datetime
import CloudFlare
import dns.resolver

def print_log(message):
	now = datetime.datetime.now().strftime("%c")
	print(now, "[auto-up-cf.py]", message)
	try:
		fh = open('./auto-up-cf.log', 'a')
		fh.write(now + " [auto-up-cf.py] " + message + "\n")
	except FileNotFoundError:
		pass

def main():
	domain = subdomain = record_type = cached_record = cached_record_id = zone_id = zone_name = None
	try:
		fh = open('./.config', 'r')
	except FileNotFoundError:
		print_log(".config not found")
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

	try:
		fh = open('./.dns-cache', 'r')
	except FileNotFoundError:
		print_log(".dns-cache not found")
		sys.exit()

	for line in fh:
		cached_record = line.split()[0]
		cached_record_id = line.split()[1]

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
			new_record = str(rdata)
	except:
		print_log("couldn't obtain IP address")

	if cached_record == new_record:
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
		if dns_record['name'] == domain:
			live_record = dns_record['content']
			live_record_id = dns_record['id']
			break

	if live_record is not None and (live_record != new_record or new_record != cached_record):
		try:
			fh = open('./.dns-cache', 'w')
			fh.write(live_record + " " + live_record_id)
		except FileNotFoundError:
			print_log(".dns-cache not found")
			sys.exit()

		log_entry = "cached CF response: " + live_record + " " + live_record_id
		print_log(log_entry)

		cf.zones.dns_records.put(zone_id,live_record_id,data={'name':domain, 'type':'A', 'content':new_record})
		print_log("updated CF")
	else:
		print_log("live record and server IP match")

if __name__ == '__main__':
	main()
