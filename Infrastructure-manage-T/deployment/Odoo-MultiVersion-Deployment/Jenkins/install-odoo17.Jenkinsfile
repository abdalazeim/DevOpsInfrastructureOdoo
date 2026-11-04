pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-org/Odoo-MultiVersion-Deployment.git'
        REPO_CREDENTIALS = 'github-credentials'
        PROJECT_ROOT = '/opt/Odoo-MultiVersion-Deployment'
        INSTANCES_CONFIG = 'versions/odoo17.yml'
        PLAYBOOK = 'ansible/playbooks/install-odoo17.yml'
        ODOO_VERSION = 'odoo17'
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    parameters {
        string(name: 'ODOO_ADMIN_PASSWORD', description: 'Odoo administrator password', trim: true)
        string(name: 'POSTGRES_PASSWORD', description: 'PostgreSQL password', trim: true)
    }

    stages {
        stage('Checkout GitHub') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/main']],
                         userRemoteConfigs: [[credentialsId: env.REPO_CREDENTIALS, url: env.REPO_URL]])
            }
        }

        stage('Pre-Deployment Validation') {
            steps {
                sh '''
                    set -e
                    docker --version
                    docker compose version
                    docker network inspect proxy >/dev/null 2>&1 || docker network create --driver bridge --subnet 172.28.0.0/16 proxy
                    df -h /opt /data
                    free -h
                    mkdir -p /opt/odoo17 /data/odoo17 /data/backups/odoo17
                    mkdir -p /data/odoo17/instance1/postgresql /data/odoo17/instance2/postgresql
                    mkdir -p /opt/odoo17/instance1/etc /opt/odoo17/instance1/addons
                    mkdir -p /opt/odoo17/instance2/etc /opt/odoo17/instance2/addons
                '''
            }
        }

        stage('Ansible Preparation') {
            steps {
                sh '''
                    set -e
                    cd ${PROJECT_ROOT}
                    ansible-galaxy collection install -r requirements.yml
                    test -f versions/odoo17.yml || { echo "ERROR: versions/odoo17.yml not found"; exit 1; }
                '''
            }
        }

        stage('Secrets Configuration') {
            steps {
                withCredentials([string(credentialsId: 'ansible-vault-password', variable: 'VAULT_PASS'),
                                 string(credentialsId: 'odoo17-admin-password', variable: 'ODOO_ADMIN_PASS'),
                                 string(credentialsId: 'odoo17-postgres-password', variable: 'POSTGRES_PASS')]) {
                    sh '''
                        set -e
                        cd ${PROJECT_ROOT}
                        cat > group_vars/vault.yml <<EOF
                        vault_odoo_admin_password: "${ODOO_ADMIN_PASS}"
                        vault_postgres_password: "${POSTGRES_PASS}"
                        EOF
                        echo "${VAULT_PASS}" > /tmp/.vault_pass; chmod 600 /tmp/.vault_pass
                        ansible-vault encrypt group_vars/vault.yml --vault-password-file /tmp/.vault_pass
                        rm -f /tmp/.vault_pass
                    '''
                }
            }
        }

        stage('Docker Deployment') {
            steps {
                withCredentials([string(credentialsId: 'ansible-vault-password', variable: 'VAULT_PASS'),
                                 string(credentialsId: 'odoo17-admin-password', variable: 'ODOO_ADMIN_PASS'),
                                 string(credentialsId: 'odoo17-postgres-password', variable: 'POSTGRES_PASS')]) {
                    sh '''
                        set -e
                        cd ${PROJECT_ROOT}
                        echo "${VAULT_PASS}" > /tmp/.vault_pass; chmod 600 /tmp/.vault_pass
                        ansible-playbook -i ansible/inventory/hosts.ini \\
                            -e @versions/odoo17.yml \\
                            -e vault_odoo_admin_password="${ODOO_ADMIN_PASS}" \\
                            -e vault_postgres_password="${POSTGRES_PASS}" \\
                            --vault-password-file /tmp/.vault_pass \\
                            ansible/playbooks/install-odoo17.yml
                        rm -f /tmp/.vault_pass
                    '''
                }
            }
        }

        stage('Traefik Configuration') {
            steps {
                sh 'docker network inspect proxy --format "{{json .Containers}}" | python3 -m json.tool 2>/dev/null || true'
            }
        }

        stage('Health Checks') {
            steps {
                script {
                    def instances = ['instance1', 'instance2']
                    def failed = []
                    for (inst in instances) {
                        try {
                            sh script: "${PROJECT_ROOT}/scripts/health-check.sh ${inst} 8069 8072", returnStatus: true
                        } catch (Exception e) {
                            failed.add(inst)
                        }
                    }
                    if (!failed.isEmpty()) error("Health check failed: ${failed.join(', ')}")
                }
            }
        }

        stage('Deployment Report') {
            steps {
                sh '''
                    docker ps --filter "name=odoo17" --format "table {{.Names}}\t{{.Status}}"
                    echo "✓ Odoo 17 deployed successfully"
                    echo "https://odoo1.devops-odoo.com"
                    echo "https://odoo2.devops-odoo.com"
                '''
            }
        }
    }

    post {
        success { mail to: 'admin@yourdomain.com', subject: "Odoo 17 deployment success - Build ${env.BUILD_NUMBER}", body: "Odoo 17 versions deployed successfully." }
        failure { mail to: 'admin@yourdomain.com', subject: "Odoo 17 deployment failure - Build ${env.BUILD_NUMBER}", body: "Odoo 17 deployment failed." }
        always { archiveArtifacts artifacts: 'ansible/**, versions/**, scripts/**, requirements.yml', allowEmptyArchive: true }
    }
}