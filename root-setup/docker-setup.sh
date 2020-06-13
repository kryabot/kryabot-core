# env setup must be set before execution
. ./env

docker network create -d bridge $KB_NETWORK_NAME
docker volume create $KB_MOUNT_NAME