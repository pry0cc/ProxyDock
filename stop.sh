#!/bin/bash

# stops the containers
for d in $(docker ps -a | awk '$2=="vpnproxy" { print $1 }'); do docker stop $d; done

# removes the containers
for d in $(docker ps -a | awk '$2=="vpnproxy" { print $1 }'); do docker rm $d; done