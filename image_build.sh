#!/bin/bash

version=`cat IMAGE_VERSION`$1

commit_dt=`git log -1 --format=%ai`
commit_id=`git log --format="%h" -n 1`

docker  build -t goodwe_monitor:$version .
