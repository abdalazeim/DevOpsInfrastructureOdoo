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
        choice(name: 'ODOO_VERSION', choices: ['odoo17', 'odoo18', 'odoo19', 'all'], description: 'اختر إصدار Odoo للنسخ الاحتياطي', default: 'all')
        choice(name: 'INSTANCE', choices: ['instance1', 'instance2', 'all'], description: 'اختر النسخة للنسخ الاحتياطي', default: 'all')
        choice(name: 'BACKUP_TYPE', choices: ['full', 'database', 'filestore', 'configuration', 'complete-infrastructure', 'pre-update'], description: 'نوع النسخ الاحتياطي', default: 'full')
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
                    echo "بدء عملية النسخ الاحتياطي - Build #${env.BUILD_NUMBER}"
                    echo "الإصدار: ${ODOO_VERSION}"
                    echo "النسخة: ${INSTANCE}"
                    echo "نوع النسخ: ${BACKUP_TYPE}"
                    docker --version
                    docker compose version
                    df -h /data /opt
                    free -h
                    mkdir -p ${BACKUP_ROOT}
                    test -d ${PROJECT_ROOT} || { echo "ERROR: مشروع النشر غير موجود في ${PROJECT_ROOT}"; exit 1; }
                '''
            }
        }

        stage('Execute Backup') {
            steps {
                sh '''
                    set -e
                    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

                    if [ "${ODOO_VERSION}" = "all" ] || [ "${ODOO_VERSION}" = "odoo17" ]; then
                        echo "=== نسخ احتياطي لـ Odoo 17 ==="
                        for inst in instance1 instance2; do
                            if [ "${INSTANCE}" = "all" ] || [ "${INSTANCE}" = "${inst}" ]; then
                                echo "نسخ النسخة: ${inst}"
                                cd ${PROJECT_ROOT}
                                ./scripts/backup.sh ${inst} odoo17 ${BACKUP_ROOT}/odoo17/${inst}
                            fi
                        done
                    fi

                    if [ "${ODOO_VERSION}" = "all" ] || [ "${ODOO_VERSION}" = "odoo19" ]; then
                        echo "=== نسخ احتياطي لـ Odoo 19 ==="
                        for inst in instance1 instance2; do
                            if [ "${INSTANCE}" = "all" ] || [ "${INSTANCE}" = "${inst}" ]; then
                                echo "نسخ النسخة: ${inst}"
                                cd ${PROJECT_ROOT}
                                ./scripts/backup.sh ${inst} odoo19 ${BACKUP_ROOT}/odoo19/${inst}
                            fi
                        done
                    fi

                    echo "اكتملت عملية النسخ الاحتياطي في: ${BACKUP_ROOT}"
                '''
            }
        }

        stage('Verify Backup Integrity') {
            steps {
                sh '''
                    set -e
                    echo "التحقق من سلامة النسخ الاحتياطية..."
                    find ${BACKUP_ROOT} -name "checksums.sha256" -type f 2>/dev/null | while read checksum_file; do
                        backup_dir=$(dirname "${checksum_file}")
                        echo "فحص: ${backup_dir}"
                        (cd "${backup_dir}" && sha256sum -c checksums.sha256) || { echo "فشل التحقق من: ${backup_dir}"; exit 1; }
                    done
                    echo "تم التحقق من جميع النسخ الاحتياطية بنجاح"
                '''
            }
        }

        stage('Backup Report') {
            steps {
                sh '''
                    echo "=== تقرير النسخ الاحتياطي ==="
                    echo "بناء رقم: ${env.BUILD_NUMBER}"
                    echo "الإصدار: ${ODOO_VERSION}"
                    echo "النسخة: ${INSTANCE}"
                    echo "نوع النسخ: ${BACKUP_TYPE}"
                    echo "المجلد: ${BACKUP_ROOT}"
                    echo ""
                    find ${BACKUP_ROOT} -type d -name "*_*" 2>/dev/null | sort -r | head -20
                    du -sh ${BACKUP_ROOT} 2>/dev/null || true
                    echo ""
                    echo "✓ تم إكمال النسخ الاحتياطي بنجاح - Build #${env.BUILD_NUMBER}"
                '''
            }
        }
    }

    post {
        success {
            mail to: 'admin@yourdomain.com',
                 subject: "نجاح النسخ الاحتياطي - بناء ${env.BUILD_NUMBER}",
                 body: "تم إكمال النسخ الاحتياطي لـ Odoo ${ODOO_VERSION} بنجاح."
        }
        failure {
            mail to: 'admin@yourdomain.com',
                 subject: "فشل النسخ الاحتياطي - بناء ${env.BUILD_NUMBER}",
                 body: "فشل عملية النسخ الاحتياطي لـ Odoo ${ODOO_VERSION}."
        }
        always {
            archiveArtifacts artifacts: 'scripts/**, backup/**, versions/**', allowEmptyArchive: true
        }
    }
}