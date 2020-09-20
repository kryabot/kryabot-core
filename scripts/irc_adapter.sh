#!/bin/bash

BOTHOME=$WORK_DIR/kryabot
VALID_ARGS_STRING="Valid arguments: status stop start log"
STOP_FILE='.irc.stop'
MODULE=irc_adapter.py
PROCESS_LOG=krya_twitch.log
CRON_LOG=cron.log

. $WORK_DIR/scripts/common.sh $1