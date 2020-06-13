RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

TAG_SOURCE=$KB_TAG_LATEST
TAG_ROLLBACK=$KB_TAG_ROLLBACK
CONTAINER_NAME=$KB_MAIN_CONTAINER

echo -e "${GREEN}[KryaBot] Updating..."
docker image prune -f > /dev/null
docker tag $TAG_SOURCE $TAG_ROLLBACK > /dev/null
echo -e "${GREEN}[KryaBot] Backuping previous tag..."
docker push $TAG_ROLLBACK > /dev/null
echo -e "${GREEN}[KryaBot] Downloading new tag..."
docker pull $TAG_SOURCE > /dev/null
#docker ps
echo -e "${GREEN}[KryaBot] Stopping old container..."
docker stop $CONTAINER_NAME > /dev/null
docker rm $CONTAINER_NAME > /dev/null
echo -e "${GREEN}[KryaBot] Starting new container..."
docker run -dit --name $CONTAINER_NAME --mount source=$KB_MOUNT_NAME,target=$KB_MOUNT_TARGET -p 5000:5000 -p 5050:5050 --network $KB_NETWORK_NAME $TAG_SOURCE
echo -e "${GREEN}[KryaBot] Started. Output:"
docker logs -f $CONTAINER_NAME