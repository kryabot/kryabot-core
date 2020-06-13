#!/bin/bash

BOTHOME=$WORK_DIR/kryabot
VALID_ARGS_STRING="Valid arguments: status stop start log"
STOP_FILE='.tg.stop'
MODULE=tg_bot.py
PROCESS_LOG=krya_tg.log
CRON_LOG=cron.log

. $WORK_DIR/scripts/common.sh $1