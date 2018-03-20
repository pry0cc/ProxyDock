#!/bin/bash

for d in $(docker ps | awk '{ print $14 }'); do docker stop $d; done
