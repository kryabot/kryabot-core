#!/bin/bash

cd $WORK_DIR

start_script(){
	name=$1
	./scripts/$name start -D
	status=$?
	if [ $status -ne 0 ]; then
	  echo "Failed to start $name: $status"
	  exit $status
	fi
}

start_script info_bot.sh
start_script guard_bot.sh

echo "Started."
while sleep 60; do
	sleep 60
done