#!/bin/sh

echo "nameserver 8.8.8.8" > /etc/resolv.conf
openvpn /$vpn
