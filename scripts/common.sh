##
#	Common functions
##
get_pid(){
	pid=${1//$STOP_FILE/''}
	pid=${pid//'./'/''}
	echo "$pid"
}

process_start() {
	nohup python $BOTHOME/$MODULE >> $MODULE.txt 2>> $MODULE.err &
	echo "" > $!$STOP_FILE
}

process_start_direct(){
	python $BOTHOME/$MODULE >> $MODULE.txt 2>> $MODULE.err
}

process_status(){
	echo 'Running processes:'
	
	for i in $(find . -name '*'$STOP_FILE ); 
	do

		pid=$( get_pid $i)

		if ps -p $pid > /dev/null
		then
			echo 'PID ' $pid
		fi
	done
}


process_stop() {
	echo 'Stopping...'
	
	for i in $(find . -name '*'$STOP_FILE ); 
	do
		echo 'Found stop file: ' $i
		pid=$( get_pid $i)
		echo 'Killing pid ' $pid
		kill -9 $pid
		rm -rf $i
	done
}

cron_check(){
	do_start=0
	
	echo '' >> $CRON_LOG
	echo `date +%R\ ` 'Start cron check' >> $CRON_LOG
	
	for i in $(find . -name '*'$STOP_FILE ); 
	do
		pid=$( get_pid $i)

		if ! ps -p $pid > /dev/null
		then
			echo "Found file $i without active process PID $pid. Removing stop file."  >> $CRON_LOG
			rm -rf $i
			do_start=1
		fi
		
	done

	if [ "$do_start" -eq 1 ]; then
		echo 'Starting bot.' $pid >> $CRON_LOG
		process_start
	fi
	
	echo `date +%R\ ` 'End cron check' >> $CRON_LOG
	exit
}

if [ -z "$1" ]
  then
    echo "No argument supplied" 
	echo $VALID_ARGS_STRING
	exit
fi

if [ $1 == "status" ]; then
	process_status
	exit
fi

if [ $1 == "start" ]; then
	process_start
	exit
fi

if [ $1 == "startdirect" ]; then
	process_start_direct
	exit
fi

if [ $1 == "stop" ]; then
	process_stop
	exit
fi

if [ $1 == "log" ]; then
	tail -f $PROCESS_LOG.log
	exit
fi

if [ $1 == "cron" ]; then
	cron_check
	exit
fi

echo 'Received unknown param: ' $1
echo $VALID_ARGS_STRING
