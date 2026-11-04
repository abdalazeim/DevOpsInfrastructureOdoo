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
        booleanParam(name: 'ENCRYPT_BACKUP', defaultValue: true, description: 'تشفير الأرشيف قبل التخزين')
        string(name: 'ENCRYPT_PASSWORD', defaultValue: '', description: 'كلمة مرور التشفير (إذا تركت فارغة سيتم استخدام القيمة الافتراضية)')
        choice(name: 'VERIFY_ONLY', choices: ['true', 'false'], description: 'فحص فقط دون نسخ احتياطي', default: 'false')
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
                    echo "بدء نسخ إعدادات نظام Ubuntu - بناء #${env.BUILD_NUMBER}"
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
                    echo "فحص النسخ الاحتياطية الحالية فقط..."
                    if [ -d /data/backups/system-config ]; then
                        ls -lh /data/backups/system-config/
                        find /data/backups/system-config -name "checksums.sha256" -exec sh -c 'cd "$(dirname {})" && sha256sum -c checksums.sha256' \;
                    else
                        echo "لا توجد نسخ احتياطية سابقة."
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
                        
                        echo "تشغيل سكربت نسخ إعدادات نظام Ubuntu..."
                        sudo /opt/Odoo-MultiVersion-Deployment/scripts/backup-system-config.sh
                        
                        echo ""
                        echo "فحص سلامة الأرشيف المُنشأ..."
                        LATEST_BACKUP=$(ls -dt /data/backups/system-config/*/ | head -1)
                        if [ -f "${LATEST_BACKUP}checksums.sha256" ]; then
                            cd "${LATEST_BACKUP}"
                            sha256sum -c checksums.sha256
                            echo "✓ تم التحقق من سلامة النسخة الاحتياطية"
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
                    echo "تشفير الأرشيف..."
                    LATEST_ARCHIVE=$(ls -dt /data/backups/system-config/system-config-*.tar.gz | head -1)
                    if [ -f "$LATEST_ARCHIVE" ]; then
                        echo "${ENCRYPT_PASSWORD}" | gpg --batch --yes --passphrase-fd 0 -c "$LATEST_ARCHIVE"
                        rm -f "$LATEST_ARCHIVE"
                        echo "✓ تم تشفير الأرشيف: ${LATEST_ARCHIVE}.gpg"
                    fi
                '''
            }
        }

        stage('Backup Report') {
            steps {
                sh '''
                    set -e
                    echo "======================================"
                    echo "تقرير نسخ إعدادات نظام Ubuntu"
                    echo "======================================"
                    echo "بناء رقم: ${env.BUILD_NUMBER}"
                    echo "التاريخ: $(date)"
                    echo "التشفير: ${ENCRYPT_BACKUP}"
                    echo ""
                    echo "النسخ المتاحة في /data/backups/system-config/:"
                    ls -lh /data/backups/system-config/ 2>/dev/null || true
                    echo ""
                    echo "✓ تم إكمال نسخ إعدادات نظام Ubuntu بنجاح"
                '''
            }
        }
    }

    post {
        success {
            mail to: 'admin@yourdomain.com',
                 subject: "نجاح نسخ إعدادات نظام Ubuntu - بناء ${env.BUILD_NUMBER}",
                 body: "تم نسخ إعدادات نظام Ubuntu بنجاح. التشفير: ${ENCRYPT_BACKUP}."
        }
        failure {
            mail to: 'admin@yourdomain.com',
                 subject: "فشل نسخ إعدادات نظام Ubuntu - بناء ${env.BUILD_NUMBER}",
                 body: "فشل نسخ إعدادات نظام Ubuntu. يرجى التحقق من السجلات."
        }
        always {
            archiveArtifacts artifacts: 'scripts/**, backup/**', allowEmptyArchive: true
        }
    }
}