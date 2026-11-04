pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-org/Odoo-MultiVersion-Deployment.git'
        REPO_CREDENTIALS = 'github-credentials'
        BACKUP_ROOT = '/data/backups'
        ODOO_VERSIONS = 'odoo17,odoo19'
        INSTANCES = 'instance1,instance2'
        PROJECT_ROOT = '/opt/Odoo-MultiVersion-Deployment'
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
    }

    parameters {
        choice(name: 'ODOO_VERSION', choices: ['odoo17', 'odoo18', 'odoo19', 'all'], description: 'Select Odoo version for backup', default: 'all')
        choice(name: 'INSTANCE', choices: ['instance1', 'instance2', 'all'], description: 'Select instance for backup', default: 'all')
        choice(name: 'BACKUP_TYPE', choices: ['full', 'database', 'filestore', 'configuration', 'complete-infrastructure', 'pre-update'], description: 'Backup type', default: 'full')
    }

    stages {
        stage('Checkout GitHub') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/main']],
                         userRemoteConfigs: [[credentialsId: env.REPO_CREDENTIALS, url: env.REPO_URL]])
            }
        }

        stage('Pre-Backup Validation') {
            steps {
                sh '''
                    set -e
                    echo "Starting backup process - Build #${env.BUILD_NUMBER}"
                    echo "Version: ${ODOO_VERSION}"
                    echo "Instance: ${INSTANCE}"
                    echo "Backup type: ${BACKUP_TYPE}"
                    docker --version
                    docker compose version
                    df -h /data /opt
                    free -h
                    mkdir -p ${BACKUP_ROOT}
                    test -d ${PROJECT_ROOT} || { echo "ERROR: Deployment project not found in ${PROJECT_ROOT}"; exit 1; }
                '''
            }
        }

        stage('Execute Backup') {
            steps {
                sh '''
                    set -e
                    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

                    if [ "${ODOO_VERSION}" = "all" ] || [ "${ODOO_VERSION}" = "odoo17" ]; then
                        echo "=== Odoo 17 Backup ==="
                        for inst in instance1 instance2; do
                            if [ "${INSTANCE}" = "all" ] || [ "${INSTANCE}" = "${inst}" ]; then
                                echo "Backing up instance: ${inst}"
                                cd ${PROJECT_ROOT}
                                ./scripts/backup.sh ${inst} odoo17 ${BACKUP_ROOT}/odoo17/${inst}
                            fi
                        done
                    fi

                    if [ "${ODOO_VERSION}" = "all" ] || [ "${ODOO_VERSION}" = "odoo19" ]; then
                        echo "=== Odoo 19 Backup ==="
                        for inst in instance1 instance2; do
                            if [ "${INSTANCE}" = "all" ] || [ "${INSTANCE}" = "${inst}" ]; then
                                echo "Backing up instance: ${inst}"
                                cd ${PROJECT_ROOT}
                                ./scripts/backup.sh ${inst} odoo19 ${BACKUP_ROOT}/odoo19/${inst}
                            fi
                        done
                    fi

                    echo "Backup process completed at: ${BACKUP_ROOT}"
                '''
            }
        }

        stage('Verify Backup Integrity') {
            steps {
                sh '''
                    set -e
                    echo "Verifying backup integrity..."
                    find ${BACKUP_ROOT} -name "checksums.sha256" -type f 2>/dev/null | while read checksum_file; do
                        backup_dir=$(dirname "${checksum_file}")
                        echo "Checking: ${backup_dir}"
                        (cd "${backup_dir}" && sha256sum -c checksums.sha256) || { echo "Verification failed for: ${backup_dir}"; exit 1; }
                    done
                    echo "All backups verified successfully"
                '''
            }
        }

        stage('Backup Report') {
            steps {
                sh '''
                    echo "=== Backup Report ==="
                    echo "Build Number: ${env.BUILD_NUMBER}"
                    echo "Version: ${ODOO_VERSION}"
                    echo "Instance: ${INSTANCE}"
                    echo "Backup type: ${BACKUP_TYPE}"
                    echo "Directory: ${BACKUP_ROOT}"
                    echo ""
                    find ${BACKUP_ROOT} -type d -name "*_*" 2>/dev/null | sort -r | head -20
                    du -sh ${BACKUP_ROOT} 2>/dev/null || true
                    echo ""
                    echo "✓ Backup completed successfully - Build #${env.BUILD_NUMBER}"
                '''
            }
        }
    }

    post {
        success {
            mail to: 'admin@yourdomain.com',
                 subject: "Backup success - Build ${env.BUILD_NUMBER}",
                 body: "Odoo ${ODOO_VERSION} backup completed successfully."
        }
        failure {
            mail to: 'admin@yourdomain.com',
                 subject: "Backup failure - Build ${env.BUILD_NUMBER}",
                 body: "Odoo ${ODOO_VERSION} backup process failed."
        }
        always {
            archiveArtifacts artifacts: 'scripts/**, backup/**, versions/**', allowEmptyArchive: true
        }
    }
}