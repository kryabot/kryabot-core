# Docker for python bot - Kryabot
# Same container used multiple time with different entry points

FROM python:3.8-alpine
RUN python --version &&\
	pip install -U pip &&\
	apk update &&\
	apk add curl \
			bash \
			vim \
			less \
			ffmpeg \
			zlib-dev \
			jpeg-dev \
			libffi-dev \
			openssl-dev \
			musl-dev \
			make \
			gcc \
			g++ 
	
	
COPY requirements.txt .
RUN pip install -r requirements.txt && pip install -U https://github.com/LonamiWebs/Telethon/archive/master.zip && ln -s /usr/share/zoneinfo/Etc/GMT+3 /etc/localtime

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

# Webserver
EXPOSE 5000

# Start up script
COPY scripts/dockerstart_irc.sh scripts/dockerstart_telegram.sh scripts/dockerstart_twitch.sh /
RUN chmod +x scripts/* && chmod +x /dockerstart_irc.sh && chmod +x /dockerstart_telegram.sh && chmod +x /dockerstart_twitch.sh

CMD /dockerstart.sh