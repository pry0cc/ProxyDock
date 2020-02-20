#!/bin/bash

echo "
random_chain
proxy_dns 
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
[ProxyList]
" > proxychains.conf 
count=5000; for f in $(cd VPN; bash -c ls); do count=$((count+1)); echo "http 127.0.0.1 $count" >> proxychains.conf; docker run -d --privileged -p 127.0.0.1:$count:8080 -e "vpn=$f" vpnproxy; done
