pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-org/Odoo-MultiVersion-Deployment.git'
        REPO_CREDENTIALS = 'github-credentials'
        BACKUP_ROOT = '/data/backups/system-config'
        ENCRYPT_PASSWORD = 'system-backup-encrypt-password'
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: 'ENCRYPT_BACKUP', defaultValue: true, description: 'Encrypt archive before storage')
        string(name: 'ENCRYPT_PASSWORD', defaultValue: '', description: 'Encryption password (if left empty, default value will be used)')
        choice(name: 'VERIFY_ONLY', choices: ['true', 'false'], description: 'Verify only without backup', default: 'false')
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
                    echo "Starting Ubuntu system configuration backup - Build #$BUILD_NUMBER"
                    whoami
                    df -h / /data /opt
                    free -h
                    mkdir -p /data/backups/system-config
                '''
            }
        }

        stage('Verify Existing Backups') {
            when {
                expression { params.VERIFY_ONLY == 'true' }
            }
            steps {
                sh '''
                    set -e
                    echo "Verifying existing backups only..."
                    if [ -d /data/backups/system-config ]; then
                        ls -lh /data/backups/system-config/
                        find /data/backups/system-config -name "checksums.sha256" -exec sh -c 'cd "$(dirname {})" && sha256sum -c checksums.sha256' \;
                    else
                        echo "No previous backups found."
                    fi
                '''
            }
        }

        stage('Execute System Config Backup') {
            when {
                expression { params.VERIFY_ONLY == 'false' }
            }
            steps {
                withCredentials([string(credentialsId: 'system-backup-encrypt-password', variable: 'ENCRYPT_PASS')]) {
                    sh '''
                        set -e
                        export ENCRYPT="${ENCRYPT_BACKUP}"
                        export ENCRYPT_PASSWORD="${ENCRYPT_PASS:-system-backup-encrypt-password}"
                        
                        echo "Running Ubuntu system configuration backup script..."
                        sudo /opt/Odoo-MultiVersion-Deployment/scripts/backup-system-config.sh
                        
                        echo "Verifying integrity of created archive..."
                        LATEST_BACKUP=$(ls -dt /data/backups/system-config/*/ | head -1)
                        if [ -f "${LATEST_BACKUP}checksums.sha256" ]; then
                            cd "${LATEST_BACKUP}"
                            sha256sum -c checksums.sha256
                            echo "✓ Backup integrity verified"
                        fi
                    '''
                }
            }
        }

        stage('Encrypt Archive') {
            when {
                expression { params.VERIFY_ONLY == 'false' && params.ENCRYPT_BACKUP == 'true' }
            }
            steps {
                sh '''
                    set -e
                    echo "Encrypting archive..."
                    LATEST_ARCHIVE=$(ls -dt /data/backups/system-config/system-config-*.tar.gz | head -1)
                    if [ -f "$LATEST_ARCHIVE" ]; then
                        echo "${ENCRYPT_PASSWORD}" | gpg --batch --yes --passphrase-fd 0 -c "$LATEST_ARCHIVE"
                        rm -f "$LATEST_ARCHIVE"
                        echo "✓ Archive encrypted: ${LATEST_ARCHIVE}.gpg"
                    fi
                '''
            }
        }

        stage('Backup Report') {
            steps {
                sh '''
                    set -e
                    echo "======================================"
                    echo "Ubuntu System Configuration Backup Report"
                    echo "======================================"
                    echo "Build Number: $BUILD_NUMBER"
                    echo "Date: $(date)"
                    echo "Encryption: ${ENCRYPT_BACKUP}"
                    echo ""
                    echo "Available backups in /data/backups/system-config/:"
                    ls -lh /data/backups/system-config/ 2>/dev/null || true
                    echo ""
                    echo "✓ Ubuntu system configuration backup completed successfully"
                '''
            }
        }
    }

    post {
        success {
            mail to: 'admin@yourdomain.com',
                 subject: "Ubuntu system configuration backup success - Build ${env.BUILD_NUMBER}",
                 body: "Ubuntu system configuration backed up successfully. Encryption: ${ENCRYPT_BACKUP}."
        }
        failure {
            mail to: 'admin@yourdomain.com',
                 subject: "Ubuntu system configuration backup failure - Build ${env.BUILD_NUMBER}",
                 body: "Ubuntu system configuration backup failed. Please check logs."
        }
        always {
            archiveArtifacts artifacts: 'scripts/**, backup/**', allowEmptyArchive: true
        }
    }
}