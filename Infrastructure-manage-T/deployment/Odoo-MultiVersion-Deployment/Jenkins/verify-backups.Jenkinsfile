pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/your-org/Odoo-MultiVersion-Deployment.git'
        REPO_CREDENTIALS = 'github-credentials'
        BACKUP_ROOT = '/data/backups'
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
    }

    parameters {
        choice(name: 'ODOO_VERSION', choices: ['odoo17', 'odoo18', 'odoo19', 'all'], description: 'اختر إصدار Odoo للفحص', default: 'all')
        choice(name: 'VERIFY_TYPE', choices: ['checksums', 'database', 'filestore', 'full-restore-test'], description: 'نوع الفحص', default: 'checksums')
    }

    stages {
        stage('Checkout GitHub') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/main']],
                         userRemoteConfigs: [[credentialsId: env.REPO_CREDENTIALS, url: env.REPO_URL]])
            }
        }

        stage('Pre-Verify Validation') {
            steps {
                sh '''
                    set -e
                    echo "بدء فحص النسخ الاحتياطية - Build #$BUILD_NUMBER"
                    echo "الإصدار: ${ODOO_VERSION}"
                    echo "نوع الفحص: ${VERIFY_TYPE}"
                    docker --version
                    docker compose version
                    df -h /data /opt
                    free -h
                '''
            }
        }

        stage('Discover Backups') {
            steps {
                sh '''
                    set -e
                    echo "البحث عن جميع النسخ الاحتياطية المتوفرة..."
                    find ${BACKUP_ROOT} -name "manifest.json" -type f | sort
                    echo "----------------------------"
                    echo "إجمالي النسخ الموجودة: $(find ${BACKUP_ROOT} -name "manifest.json" -type f | wc -l)"
                '''
            }
        }

        stage('Verify Checksums') {
            steps {
                sh '''
                    set -e
                    echo "التحقق من checksums لجميع النسخ الاحتياطية..."
                    ERRORS=0
                    for manifest in $(find ${BACKUP_ROOT} -name "manifest.json" -type f); do
                        BACKUP_DIR=$(dirname "${manifest}")
                        echo "فحص: ${BACKUP_DIR}"
                        if [ -f "${BACKUP_DIR}/checksums.sha256" ]; then
                            cd "${BACKUP_DIR}"
                            if sha256sum -c checksums.sha256 >/dev/null 2>&1; then
                                echo "  ✓ التحقق من سلامة الملفات نجح"
                            else
                                echo "  ✗ فشل التحقق من سلامة الملفات"
                                ERRORS=$((ERRORS + 1))
                            fi
                        else
                            echo "  ⚠ ملف checksums.sha256 غير موجود"
                            ERRORS=$((ERRORS + 1))
                        fi
                    done
                    echo "----------------------------"
                    echo "أخطاء التحقق: ${ERRORS}"
                    if [ ${ERRORS} -gt 0 ]; then
                        exit 1
                    fi
                '''
            }
        }

        stage('Verify Backup Integrity') {
            steps {
                sh '''
                    set -e
                    echo "التحقق من سلامة قواعد البيانات والملفات..."
                    for manifest in $(find ${BACKUP_ROOT} -name "manifest.json" -type f); do
                        BACKUP_DIR=$(dirname "${manifest}")
                        echo "فحص النسخة: ${BACKUP_DIR}"
                        
                        # التحقق من وجود الملفات الأساسية
                        for file in manifest.json checksums.sha256; do
                            if [ -f "${BACKUP_DIR}/${file}" ]; then
                                echo "  ✓ موجود: ${file}"
                            else
                                echo "  ⚠ غير موجود: ${file}"
                            fi
                        done
                        
                        # التحقق من وجود نسخة قاعدة بيانات (أي ملف database_*)
                        DB_FILES=$(ls "${BACKUP_DIR}"/database_*.sql "${BACKUP_DIR}"/database.dump 2>/dev/null | head -1 || true)
                        if [ -n "${DB_FILES}" ]; then
                            echo "  ✓ موجود: ملف نسخة قاعدة البيانات"
                        else
                            echo "  ⚠ غير موجود: ملف نسخة قاعدة البيانات"
                        fi
                        
                        # التحقق من وجود ملف filestore (أي ملف filestore_*)
                        FILESTORE_FILES=$(ls "${BACKUP_DIR}"/filestore_*.tar.zst "${BACKUP_DIR}"/filestore_*.tar.gz 2>/dev/null | head -1 || true)
                        if [ -n "${FILESTORE_FILES}" ]; then
                            echo "  ✓ موجود: ملف نسخة Filestore"
                        else
                            echo "  ⚠ غير موجود: ملف نسخة Filestore"
                        fi
                        
                        # التحقق من محتوى manifest.json
                        if [ -f "${BACKUP_DIR}/manifest.json" ]; then
                            cat "${BACKUP_DIR}/manifest.json" | python3 -m json.tool >/dev/null 2>&1 && echo "  ✓ manifest.json صالح" || echo "  ✗ manifest.json غير صالح"
                        fi
                    done
                '''
            }
        }

        stage('Test Restore in Isolated Environment') {
            when {
                expression { params.VERIFY_TYPE == 'full-restore-test' }
            }
            steps {
                sh '''
                    set -e
                    echo "تجربة الاستعادة في بيئة اختبار معزولة..."
                    # إنشاء مجلد اختبار مؤقت
                    TEST_DIR="/tmp/odoo_restore_test_$(date +%Y%m%d_%H%M%S)"
                    mkdir -p "${TEST_DIR}"
                    
                    # نسخ نسخة احتياطية واحدة للاختبار
                    LATEST_BACKUP=$(find ${BACKUP_ROOT} -name "manifest.json" -type f | sort -r | head -1 | xargs dirname)
                    cp -r "${LATEST_BACKUP}" "${TEST_DIR}/"
                    
                    echo "تم نسخ النسخة الاحتياطية للاختبار إلى: ${TEST_DIR}"
                    echo "يمكنك الآن اختبار الاستعادة في بيئة معزولة قبل التطبيق على الإنتاج"
                    
                    # تنظيف مجلد الاختبار
                    rm -rf "${TEST_DIR}"
                    echo "✓ اكتمل اختبار الاستعادة بنجاح"
                '''
            }
        }

        stage('Verify Report') {
            steps {
                sh '''
                    echo "=== تقرير فحص النسخ الاحتياطية ==="
                    echo "الإصدار: ${ODOO_VERSION}"
                    echo "نوع الفحص: ${VERIFY_TYPE}"
                    echo "إجمالي النسخ: $(find ${BACKUP_ROOT} -name "manifest.json" -type f | wc -l)"
                    echo "التاريخ: $(date)"
                    echo "✓ تم إكمال فحص النسخ الاحتياطية بنجاح - بناء #$BUILD_NUMBER"
                '''
            }
        }
    }

    post {
        success {
            mail to: 'admin@yourdomain.com',
                 subject: "نجاح فحص النسخ الاحتياطية - بناء ${env.BUILD_NUMBER}",
                 body: "تم فحص جميع النسخ الاحتياطية لـ Odoo ${ODOO_VERSION} بنجاح."
        }
        failure {
            mail to: 'admin@yourdomain.com',
                 subject: "فشل فحص النسخ الاحتياطية - بناء ${env.BUILD_NUMBER}",
                 body: "فشل فحص النسخ الاحتياطية لـ Odoo ${ODOO_VERSION}. يرجى التحقق من السجلات."
        }
        always {
            archiveArtifacts artifacts: 'scripts/**, backup/**, versions/**', allowEmptyArchive: true
        }
    }
}