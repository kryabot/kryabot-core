# Docker for python bot - Kryabot
FROM python:latest
RUN python --version &&\
	apt-get update &&\
	apt-get install curl &&\
	apt-get -y install vim &&\
	apt-get -y install less &&\
	apt-get -y install ffmpeg
COPY requirements.txt .
RUN pip install -r requirements.txt && pip install -U https://github.com/LonamiWebs/Telethon/archive/master.zip

# Environment variables
ENV WORK_DIR="/opt/app/kb"
ENV SECRET_DIR=$WORK_DIR/secret/
ENV LOG_DIR=$WORK_DIR/log/
ENV TZ=GMT-3
WORKDIR $WORK_DIR

# Move needed files
COPY log log
COPY kryabot kryabot
COPY scripts scripts
RUN /bin/bash -c 'chmod +x scripts/*'

# Twitch webhook
EXPOSE 5050
# Flask for telegram webhook
EXPOSE 5000

# Start up script
COPY scripts/dockerstart.sh /
RUN chmod +x /dockerstart.sh

CMD /dockerstart.sh