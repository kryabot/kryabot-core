#!/bin/bash

BOTHOME=$WORK_DIR/kryabot
VALID_ARGS_STRING="Valid arguments: status stop start log"
STOP_FILE='.info.stop'
MODULE=info_bot.py
PROCESS_LOG=krya_info.log
CRON_LOG=cron.log

. $WORK_DIR/scripts/common.sh $1