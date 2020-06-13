REPO=redis:latest
POD_NAME=redis_pod

docker ps
docker stop $POD_NAME
docker rm $POD_NAME
docker pull $REPO
docker run -dit \
	--name $POD_NAME \
	-e REDIS_PASSWORD=$KB_REDIS_PASSWORD \
	-v /opt/app/kb/redis_cache:/data \
	-p 6379:6379 \
	--network $KB_NETWORK_NAME \
	--restart always \
	$REPO \
	/bin/sh -c 'redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}'