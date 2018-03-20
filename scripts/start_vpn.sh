#!/bin/bash

echo "nameserver 8.8.8.8" > /etc/resolv.conf

openvpn /VPN/$vpn
