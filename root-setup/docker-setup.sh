# env setup must be set before execution
. ./env

docker network create -d bridge $KB_NETWORK_NAME
docker volume create $KB_MOUNT_NAME
docker volume create $KB_MOUNT_LOG_NAME
ln -s /var/lib/docker/volumes/$KB_MOUNT_LOG_NAME/_data logs