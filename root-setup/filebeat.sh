
docker stop filebeat
docker rm filebeat
curl https://raw.githubusercontent.com/logzio/public-certificates/master/AAACertificateServices.crt --create-dirs -o COMODORSADomainValidationSecureServerCA.crt
docker run -dit --user root --name filebeat --volume="$(pwd)/filebeat.yaml:/usr/share/filebeat/filebeat.yml:ro" --volume="/root/logs:/tmp/logs:ro" --volume="$(pwd)/COMODORSADomainValidationSecureServerCA.crt:/etc/pki/tls/certs/COMODORSADomainValidationSecureServerCA.crt" docker.elastic.co/beats/filebeat:7.15.0