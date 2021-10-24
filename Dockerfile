# Docker for python bot - Kryabot
# Same container used multiple time with different entry points

FROM python:3.9-alpine
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
            chromium-chromedriver \
			g++ &&\
    rm -rf /var/cache/apk/*
	
	



# Environment variables
ENV WORK_DIR="/opt/app/kb" \
    SECRET_DIR=$WORK_DIR/secret/ \
    LOG_DIR=$WORK_DIR/log/ \
    TZ=GMT-3

WORKDIR $WORK_DIR

# Move needed files
COPY requirements.txt .
COPY log log
COPY kryabot kryabot
COPY scripts scripts
COPY scripts/ /

# Webserver
EXPOSE 5000

# Start up script

RUN pip install -r requirements.txt &&\
    pip install -U https://github.com/LonamiWebs/Telethon/archive/master.zip &&\
    ln -s /usr/share/zoneinfo/Etc/GMT+3 /etc/localtime && \
    chmod +x scripts/* &&  \
    chmod +x /dockerstart_*.sh &&  \
    sed -i -e 's/\r$//' /dockerstart_*.sh && \
    sed -i -e 's/\r$//' scripts/*.sh

CMD /dockerstart.sh