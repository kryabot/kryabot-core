docker pull oskaras/kryabot:20190812
docker ps
docker stop kryabot_pod
docker rm kryabot_pod
docker run -dit --name kryabot_pod --mount source=kryabot-secret,target=/opt/app/kb/secret -p 5000:5000 -p 5050:5050 --network app-tier oskaras/kryabot:20190812
