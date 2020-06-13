REPO=oskaras/kryabot:kryaweb
POD_NAME=kryaweb_pod

docker ps
docker stop $POD_NAME
docker rm $POD_NAME
docker pull $REPO
docker run -dit --name $POD_NAME -p 80:80 $REPO