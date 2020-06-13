#!/bin/bash

cd $WORK_DIR
./scripts/all start

exec "$@"