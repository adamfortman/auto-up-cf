# Auto Update CloudFlare

simple script to detect your home's public IP address and compare to a DNS record of your choosing, updating if different

# Expected workflow

- get public IP
- get DNS record
- if different, use CF API to update record with new address

# Todo

- add error checks
	- right now it just works because i went step by step making sure it works for my specific need
