RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

LABEL="[KryaBot]"
TAG_SOURCE=$KB_TAG_LATEST
TAG_ROLLBACK=$KB_TAG_ROLLBACK
CONTAINER_NAME=$KB_MAIN_CONTAINER
CONTAINER_NAME_IRC=irc
CONTAINER_NAME_TWITCH=twitch
CONTAINER_NAME_TELEGRAM=telegram
CONTAINER_NAME_INFOMANAGER=infomanager

UPDATE_CONTAINER=${1:-all}

log(){
    echo -e "${GREEN}${LABEL}${NC} $1"
}

stop_container(){
    log "Stopping $1 container"
    docker stop kryabot_$1 > /dev/null
    docker rm kryabot_$1 > /dev/null
}

start_container(){
    log "Starting container ${1}"
    docker run -dit --name kryabot_$1 --env KB_APP=$1 --env KB_LOG_DIR=$KB_MOUNT_LOG_TARGET --mount source=$KB_MOUNT_NAME,target=$KB_MOUNT_TARGET --mount source=$KB_MOUNT_LOG_NAME,target=$KB_MOUNT_LOG_TARGET --network $KB_NETWORK_NAME --entrypoint "/dockerstart_${1}.sh" $TAG_SOURCE
}

start_container_telegram(){
    log "Starting container ${CONTAINER_NAME_TELEGRAM}"
    docker run -dit --name kryabot_${CONTAINER_NAME_TELEGRAM} --env KB_APP=${CONTAINER_NAME_TELEGRAM} --env KB_LOG_DIR=$KB_MOUNT_LOG_TARGET --mount source=$KB_MOUNT_NAME,target=$KB_MOUNT_TARGET --mount source=$KB_MOUNT_LOG_NAME,target=$KB_MOUNT_LOG_TARGET -p 5000:5000 --network $KB_NETWORK_NAME --entrypoint "/dockerstart_${CONTAINER_NAME_TELEGRAM}.sh" $TAG_SOURCE
}


update(){
   log "Updating... ${UPDATE_CONTAINER}"
   docker image prune -f > /dev/null
   docker tag $TAG_SOURCE $TAG_ROLLBACK > /dev/null

   log "Backing up previous tag..."
   docker push $TAG_ROLLBACK > /dev/null

   log "Downloading new tag..."
   docker pull $TAG_SOURCE > /dev/null
   

   if [ "$UPDATE_CONTAINER" = "all" ] || [ "$UPDATE_CONTAINER" = "$CONTAINER_NAME_IRC" ]; then
      stop_container ${CONTAINER_NAME_IRC}
      start_container ${CONTAINER_NAME_IRC}
   fi

   if [ "$UPDATE_CONTAINER" = "all" ] || [ "$UPDATE_CONTAINER" = "$CONTAINER_NAME_TWITCH" ]; then
      stop_container ${CONTAINER_NAME_TWITCH}
      start_container ${CONTAINER_NAME_TWITCH}
   fi

   if [ "$UPDATE_CONTAINER" = "all" ] || [ "$UPDATE_CONTAINER" = "$CONTAINER_NAME_TELEGRAM" ]; then
      stop_container ${CONTAINER_NAME_TELEGRAM}
      start_container_telegram
   fi
   
   if [ "$UPDATE_CONTAINER" = "all" ] || [ "$UPDATE_CONTAINER" = "$CONTAINER_NAME_INFOMANAGER" ]; then
      stop_container ${CONTAINER_NAME_INFOMANAGER}
      start_container ${CONTAINER_NAME_INFOMANAGER}
   fi

   log "Finished!"
}

if [ "$UPDATE_CONTAINER" != "all" ] \
&& [ "$UPDATE_CONTAINER" != "$CONTAINER_NAME_IRC" ] \
&& [ "$UPDATE_CONTAINER" != "$CONTAINER_NAME_TWITCH" ] \
&& [ "$UPDATE_CONTAINER" != "$CONTAINER_NAME_TELEGRAM" ] \
&& [ "$UPDATE_CONTAINER" != "$CONTAINER_NAME_INFOMANAGER" ]; then
  log "Bad input app name ${UPDATE_CONTAINER}. Supported values: all ${CONTAINER_NAME_IRC} ${CONTAINER_NAME_TWITCH} ${CONTAINER_NAME_TELEGRAM} ${CONTAINER_NAME_INFOMANAGER}"
  exit 1
fi

update

