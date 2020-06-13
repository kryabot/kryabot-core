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

monitor_script(){
	name=$1
	ps aux |grep &1 |grep -q -v grep
	PROC_STATUS=$?
	if [ $PROC_STATUS -ne 0 ]; then
		echo "Failed to detect process for script $name ($PROC_STATUS), restarting $name..."
		start_script $name
	fi
}

start_script info_bot.sh
start_script twitch_bot.sh
start_script guard_bot.sh

while sleep 60; do
	monitor_script twitch_bot.sh
	monitor_script guard_bot.sh
	monitor_script info_bot.sh
done