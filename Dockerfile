# Docker for python bot - Kryabot
# Same container used multiple time with different entry points

FROM python:latest
RUN python --version &&\
	apt-get update &&\
	apt-get install curl &&\
	apt-get -y install vim &&\
	apt-get -y install less &&\
	apt-get -y install ffmpeg &&\
	apt-get -y install libblas-dev liblapack-dev
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

# Webserver
EXPOSE 5000

# Start up script
COPY scripts/dockerstart_irc.sh /
COPY scripts/dockerstart_spam.sh /
COPY scripts/dockerstart_telegram.sh /
COPY scripts/dockerstart_twitch.sh /

RUN chmod +x /dockerstart_irc.sh && chmod +x /dockerstart_spam.sh && chmod +x /dockerstart_telegram.sh && chmod +x /dockerstart_twitch.sh

CMD /dockerstart.sh