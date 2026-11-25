#!/usr/bin/env bash
# Run on the Jenkins EC2 instance (Ubuntu 24.04): bash setup-jenkins-server.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

sudo apt-get update
sudo apt-get install -y fontconfig openjdk-21-jre git curl wget

# Jenkins LTS apt repository; if the key fails, get the current one from https://www.jenkins.io/doc/book/installing/linux/
sudo install -m 0755 -d /etc/apt/keyrings
sudo wget -qO /etc/apt/keyrings/jenkins-keyring.asc https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key
echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
    | sudo tee /etc/apt/sources.list.d/jenkins.list >/dev/null
sudo apt-get update
sudo apt-get install -y jenkins

bash "$SCRIPT_DIR/install-docker.sh"

# Lets pipelines run docker without sudo (note: docker group membership is root-equivalent).
sudo usermod -aG docker jenkins
sudo systemctl enable jenkins
sudo systemctl restart jenkins

echo
echo "Jenkins is starting on port 8080."
echo "Initial admin password:"
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
