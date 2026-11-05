pipeline {
    agent any

    environment {
        INSTALLER_LOG_DIR = "/var/log/odoo-installer"
        DRY_RUN = "false"
        USE_SUDO = "true"
    }

    stages {
        stage('Prepare Environment') {
            steps {
                script {
                    sh "mkdir -p ${INSTALLER_LOG_DIR}"
                }
            }
        }

        stage('Install Basic System Packages') {
            steps {
                script {
                    sh '''
                    apt-get update -y
                    DEBIAN_FRONTEND=noninteractive apt-get install -y \
                        curl wget gnupg software-properties-common apt-transport-https \
                        ca-certificates python3 python3-pip python3-venv git vim sudo ufw jq tar gzip zstd
                    '''
                }
                post {
                    failure {
                        script {
                            echo "WARNING: Basic packages installation failed, continuing..."
                            currentBuild.result = 'UNSTABLE'
                        }
                    }
                }
            }
        }

        stage('Install Docker Engine') {
            steps {
                script {
                    sh '''
                    install -m 0755 -d /etc/apt/keyrings
                    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
                    chmod a+r /etc/apt/keyrings/docker.gpg
                    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null
                    apt-get update -y
                    DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                    systemctl enable docker
                    systemctl start docker
                    '''
                }
                post {
                    failure {
                        script {
                            echo "WARNING: Docker installation failed, continuing..."
                            currentBuild.result = 'UNSTABLE'
                        }
                    }
                }
            }
        }

        stage('Install Ansible') {
            steps {
                script {
                    sh '''
                    python3 -m pip install --upgrade pip
                    python3 -m pip install ansible
                    '''
                }
                post {
                    failure {
                        script {
                            echo "WARNING: Ansible installation failed, continuing..."
                            currentBuild.result = 'UNSTABLE'
                        }
                    }
                }
            }
        }

        stage('Create Docker Proxy Network') {
            steps {
                script {
                    sh '''
                    docker network create --driver bridge --subnet 172.28.0.0/16 proxy 2>/dev/null || echo "Network may already exist"
                    '''
                }
                post {
                    failure {
                        script {
                            echo "WARNING: Docker network creation failed, continuing..."
                        }
                    }
                }
            }
        }

        stage('Generate Installation Report') {
            steps {
                script {
                    sh '''
                    echo "============================================================"
                    echo "  SEQUENTIAL INSTALLATION - JENKINS REPORT"
                    echo "============================================================"
                    echo ""
                    echo "Build: ${BUILD_NUMBER}"
                    echo "Job:   ${JOB_NAME}"
                    echo "Date:  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
                    echo ""
                    command -v docker >/dev/null 2>&1 && echo "[SUCCESS] Docker: $(docker --version)" || echo "[FAILED] Docker not installed"
                    docker compose version >/dev/null 2>&1 && echo "[SUCCESS] Docker Compose: $(docker compose version)" || echo "[FAILED] Docker Compose not available"
                    command -v ansible-playbook >/dev/null 2>&1 && echo "[SUCCESS] Ansible: $(ansible-playbook --version | head -1)" || echo "[FAILED] Ansible not installed"
                    command -v python3 >/dev/null 2>&1 && echo "[SUCCESS] Python3: $(python3 --version)" || echo "[FAILED] Python3 not installed"
                    docker network inspect proxy >/dev/null 2>&1 && echo "[SUCCESS] Docker network 'proxy': exists" || echo "[FAILED] Docker network 'proxy': not found"
                    echo ""
                    echo "Log directory: ${INSTALLER_LOG_DIR}"
                    echo "============================================================"
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: "${INSTALLER_LOG_DIR}/**", allowEmptyArchive: true
            script {
                def result = currentBuild.result ?: 'SUCCESS'
                echo "Final build result: ${result}"
            }
        }
        cleanup {
            sh "echo 'Sequential installation pipeline completed.'"
        }
    }
}
