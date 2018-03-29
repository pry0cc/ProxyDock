#!/bin/bash

cat <<EOF > proxychains.conf
random_chain
quiet_mode
proxy_dns 
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000

[ProxyList]
EOF

# starting port
port=5000

for f in $(find VPN -name *.ovpn); do
  echo "socks5 127.0.0.1 $port" >> proxychains.conf
  docker run -d --privileged -p 127.0.0.1:$port:1080 -e "vpn=$f" pry0cc/proxydock
  port=$((port+1))
done
