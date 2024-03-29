export KB_IP=$(ip a | grep eth0 | grep inet | awk '{print $2}' | cut -d "/" -f1)
export KB_MOUNT_NAME=kryabot-secret
export KB_MOUNT_TARGET=/opt/app/kb/secret
export KB_MOUNT_LOG_NAME=kryabot-logs
export KB_MOUNT_LOG_TARGET=/tmp/logs
export KB_MAIN_CONTAINER=kryabot_pod
export KB_NETWORK_NAME=app-tier
export KB_REDIS_PASSWORD=random4444
export KB_TAG_LATEST=oskaras/kryabot:latest
export KB_TAG_ROLLBACK=oskaras/kryabot:rollback
export KB_POSTGRES_PASSWORD=gdt345h7f32dv3fs
export KB_POSTGRES_USER=kb
