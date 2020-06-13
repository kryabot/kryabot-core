#!/bin/bash

echo Updating OS...
apt-get update > /dev/null

echo Installing apps...
sudo apt-get install apt-transport-https ca-certificates curl gnupg-agent software-properties-common -y

echo Installing docker...
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
sudo apt-get update > /dev/null
sudo apt-get install docker-ce docker-ce-cli containerd.io -y

echo Checking docker status...
systemctl status docker | grep "Active:"
echo Starting hello-world image as test
sudo docker run hello-world | grep -A 1 "Hello"