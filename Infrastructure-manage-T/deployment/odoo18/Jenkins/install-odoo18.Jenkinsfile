pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-org/Odoo-MultiVersion-Deployment.git'
        REPO_CREDENTIALS = 'github-credentials'
        ANSIBLE_VAULT_PASSWORD = 'ansible-vault-password'
        ODOO_ADMIN_PASSWORD = credentials('odoo18-admin-password')
        POSTGRES_PASSWORD = credentials('odoo18-postgres-password')
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
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
                    mkdir -p /opt/odoo18 /data/odoo18 /data/backups/odoo18
                    mkdir -p /data/odoo18/instance1/postgresql /data/odoo18/instance2/postgresql
                    mkdir -p /opt/odoo18/instance1/etc /opt/odoo18/instance1/addons
                    mkdir -p /opt/odoo18/instance2/etc /opt/odoo18/instance2/addons
                '''
            }
        }

        stage('Ansible Preparation') {
            steps {
                sh '''
                    set -e
                    ansible-galaxy collection install -r requirements.yml
                    test -f versions/odoo18.yml || { echo "ERROR: versions/odoo18.yml غير موجود"; exit 1; }
                '''
            }
        }

        stage('Secrets Configuration') {
            steps {
                withCredentials([string(credentialsId: 'ansible-vault-password', variable: 'VAULT_PASS')]) {
                    sh '''
                        set -e
                        cat > group_vars/vault.yml <<EOF
                        vault_odoo_admin_password: "${ODOO_ADMIN_PASSWORD}"
                        vault_postgres_password: "${POSTGRES_PASSWORD}"
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
                withCredentials([string(credentialsId: 'ansible-vault-password', variable: 'VAULT_PASS')]) {
                    sh '''
                        set -e
                        echo "${VAULT_PASS}" > /tmp/.vault_pass; chmod 600 /tmp/.vault_pass
                        ansible-playbook -i ansible/inventory/hosts.ini \\
                            -e @versions/odoo18.yml \\
                            -e vault_odoo_admin_password="${ODOO_ADMIN_PASSWORD}" \\
                            -e vault_postgres_password="${POSTGRES_PASSWORD}" \\
                            --vault-password-file /tmp/.vault_pass \\
                            ansible/playbooks/install-odoo18.yml
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
                            sh script: "./scripts/health-check.sh ${inst} 8069 8072", returnStatus: true
                        } catch (Exception e) {
                            failed.add(inst)
                        }
                    }
                    if (!failed.isEmpty()) error("فشل في النسخ: ${failed.join(', ')}")
                }
            }
        }

        stage('Deployment Report') {
            steps {
                sh '''
                    docker ps --filter "name=odoo18" --format "table {{.Names}}\t{{.Status}}"
                    echo "✓ تم نشر Odoo 18 بنجاح"
                    echo "https://${ODOO18_INSTANCE1_DOMAIN:-odoo18-1.localhost}"
                    echo "https://${ODOO18_INSTANCE2_DOMAIN:-odoo18-2.localhost}"
                '''
            }
        }
    }

    post {
        success { mail to: 'admin@yourdomain.com', subject: "نجاح نشر Odoo 18 - بناء ${env.BUILD_NUMBER}", body: "تم نشر نسختي Odoo 18 بنجاح." }
        failure { mail to: 'admin@yourdomain.com', subject: "فشل نشر Odoo 18 - بناء ${env.BUILD_NUMBER}", body: "فشل نشر Odoo 18." }
        always { archiveArtifacts artifacts: 'ansible/**, versions/**, scripts/**, requirements.yml', allowEmptyArchive: true }
    }
}