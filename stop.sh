#!/bin/bash

docker ps -q | xargs docker stop
