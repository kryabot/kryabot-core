##
#	Common functions
##

process_start() {
	process_start_direct
}

process_start_direct(){
	python $BOTHOME/$MODULE >> $MODULE.txt 2>> $MODULE.err
}

if [ -z "$1" ]
  then
    echo "No argument supplied" 
	echo $VALID_ARGS_STRING
	exit
fi


if [ $1 == "start" ]; then
	process_start
	exit
fi


echo 'Received unknown param: ' $1
echo $VALID_ARGS_STRING
