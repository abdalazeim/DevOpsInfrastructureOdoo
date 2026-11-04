pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-org/Odoo-MultiVersion-Deployment.git'
        REPO_CREDENTIALS = 'github-credentials'
        BACKUP_ROOT = '/data/backups'
        PROJECT_ROOT = '/opt/Odoo-MultiVersion-Deployment'
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
    }

    parameters {
        choice(name: 'ODOO_VERSION', choices: ['odoo17', 'odoo18', 'odoo19'], description: 'اختر إصدار Odoo للاستعادة', required: true)
        choice(name: 'INSTANCE', choices: ['instance1', 'instance2'], description: 'اختر النسخة للاستعادة', required: true)
        string(name: 'BACKUP_ID', description: 'معرف النسخة الاحتياطية المراد استعادتها (مثال: odoo17-instance1-20261104)', required: true)
        booleanParam(name: 'CONFIRM_RESTORE', defaultValue: false, description: 'تأكيد الاستعادة (يجب تحديده للموافقة على الاستعادة)')
        choice(name: 'RESTORE_TYPE', choices: ['existing', 'new-instance'], description: 'نوع الاستعادة', default: 'existing')
        string(name: 'NEW_INSTANCE_NAME', description: 'اسم النسخة الجديدة (لاستعادة as New Instance)', default: '')
    }

    stages {
        stage('Checkout GitHub') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/main']],
                         userRemoteConfigs: [[credentialsId: env.REPO_CREDENTIALS, url: env.REPO_URL]])
            }
        }

        stage('Confirm Restore') {
            steps {
                script {
                    if (!params.CONFIRM_RESTORE) {
                        error("يجب تحديد خيار تأكيد الاستعادة (CONFIRM_RESTORE) للموافقة على عملية الاستعادة.")
                    }
                    echo "تم تأكيد الاستعادة - بدء العملية"
                }
            }
        }

        stage('Pre-Restore Validation') {
            steps {
                sh '''
                    set -e
                    echo "بدء عملية الاستعادة - Build #${env.BUILD_NUMBER}"
                    echo "الإصدار: ${ODOO_VERSION}"
                    echo "النسخة: ${INSTANCE}"
                    echo "معرف النسخة الاحتياطية: ${BACKUP_ID}"
                    echo "نوع الاستعادة: ${RESTORE_TYPE}"
                    docker --version
                    docker compose version
                    df -h /data /opt
                    free -h
                    test -d ${PROJECT_ROOT} || { echo "ERROR: مشروع النشر غير موجود"; exit 1; }
                '''
            }
        }

        stage('Verify Backup Exists') {
            steps {
                sh '''
                    set -e
                    BACKUP_PATH="${BACKUP_ROOT}/${ODOO_VERSION}/${INSTANCE}/${BACKUP_ID}"
                    if [ ! -d "${BACKUP_PATH}" ]; then
                        echo "ERROR: النسخة الاحتياطية غير موجودة: ${BACKUP_PATH}"
                        exit 1
                    fi
                    if [ ! -f "${BACKUP_PATH}/manifest.json" ]; then
                        echo "ERROR: ملف manifest.json غير موجود في النسخة الاحتياطية"
                        exit 1
                    fi
                    if [ ! -f "${BACKUP_PATH}/checksums.sha256" ]; then
                        echo "ERROR: ملف checksums.sha256 غير موجود في النسخة الاحتياطية"
                        exit 1
                    fi
                    echo "تم العثور على النسخة الاحتياطية: ${BACKUP_PATH}"
                '''
            }
        }

        stage('Verify Backup Integrity') {
            steps {
                sh '''
                    set -e
                    BACKUP_PATH="${BACKUP_ROOT}/${ODOO_VERSION}/${INSTANCE}/${BACKUP_ID}"
                    echo "التحقق من سلامة النسخة الاحتياطية عبر SHA256..."
                    cd "${BACKUP_PATH}"
                    sha256sum -c checksums.sha256
                    echo "تم التحقق من سلامة النسخة الاحتياطية بنجاح"
                '''
            }
        }

        stage('Execute Restore') {
            steps {
                sh '''
                    set -e
                    BACKUP_PATH="${BACKUP_ROOT}/${ODOO_VERSION}/${INSTANCE}/${BACKUP_ID}"
                    
                    echo "إيقاف خدمة Odoo مؤقتًا..."
                    cd ${PROJECT_ROOT}
                    ODOO_CONTAINER="${ODOO_VERSION}-${INSTANCE}"
                    DB_CONTAINER="${ODOO_VERSION}-${INSTANCE}-db"
                    
                    if docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
                        docker stop "${ODOO_CONTAINER}" 2>/dev/null || true
                        echo "تم إيقاف حاوية Odoo: ${ODOO_CONTAINER}"
                    fi

                    echo "أخذ نسخة احتياطية من الحالة الحالية قبل الاستبدال..."
                    SAFETY_DIR="${BACKUP_ROOT}/safety_pre_restore_$(date +%Y%m%d_%H%M%S)"
                    mkdir -p "${SAFETY_DIR}"
                    cp -r /data/${ODOO_VERSION}/${INSTANCE} "${SAFETY_DIR}/" 2>/dev/null || true

                    echo "استعادة نسخ احتياطية باستخدام سكريبت الاستعادة..."
                    ./scripts/restore.sh "${BACKUP_ID}" "${ODOO_VERSION}" "${INSTANCE}" "${RESTORE_TYPE}" "${NEW_INSTANCE_NAME}"

                    echo "التحقق من صحة الخدمة بعد الاستعادة..."
                    sleep 10
                    docker exec "${DB_CONTAINER}" pg_isready -U postgres -h localhost
                    
                    echo "✓ تم إكمال عملية الاستعادة بنجاح"
                '''
            }
        }

        stage('Post-Restore Verification') {
            steps {
                sh '''
                    set -e
                    echo "إجراء اختبارات التحقق بعد الاستعادة..."
                    ODOO_CONTAINER="${ODOO_VERSION}-${INSTANCE}"
                    DB_CONTAINER="${ODOO_VERSION}-${INSTANCE}-db"
                    
                    docker exec "${ODOO_CONTAINER}" wget --no-verbose --tries=1 --spider http://localhost:8069/web/database/selector
                    echo "✓ Odoo يستجيب بعد الاستعادة"
                    docker exec "${DB_CONTAINER}" pg_isready -U postgres -h localhost
                    echo "✓ PostgreSQL يستجيب بعد الاستعادة"
                '''
            }
        }

        stage('Restore Report') {
            steps {
                sh '''
                    echo "=== تقرير الاستعادة ==="
                    echo "الإصدار: ${ODOO_VERSION}"
                    echo "النسخة: ${INSTANCE}"
                    echo "معرف النسخة الاحتياطية: ${BACKUP_ID}"
                    echo "نوع الاستعادة: ${RESTORE_TYPE}"
                    echo "التاريخ: $(date)"
                    echo "✓ تم إكمال عملية الاستعادة بنجاح - بناء #${env.BUILD_NUMBER}"
                '''
            }
        }
    }

    post {
        success {
            mail to: 'admin@yourdomain.com',
                 subject: "نجاح الاستعادة - بناء ${env.BUILD_NUMBER}",
                 body: "تم استعادة نسخة Odoo ${ODOO_VERSION} ${INSTANCE} من النسخة الاحتياطية ${BACKUP_ID} بنجاح."
        }
        failure {
            mail to: 'admin@yourdomain.com',
                 subject: "فشل الاستعادة - بناء ${env.BUILD_NUMBER}",
                 body: "فشل عملية استعادة نسخة Odoo ${ODOO_VERSION} ${INSTANCE}. يرجى التحقق من السجلات."
        }
        always {
            archiveArtifacts artifacts: 'scripts/**, backup/**, versions/**', allowEmptyArchive: true
        }
    }
}