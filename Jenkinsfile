pipeline {
    agent any

    environment {
        VENV_DIR = 'venv'
        APP_PORT = '8000'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv $VENV_DIR
                    . $VENV_DIR/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . $VENV_DIR/bin/activate
                    python manage.py test
                '''
            }
        }

        stage('Run / Deploy') {
            steps {
                sh '''
                    . $VENV_DIR/bin/activate

                    # Если старый процесс ещё жив — гасим
                    if [ -f django.pid ]; then
                        kill $(cat django.pid) || true
                        rm -f django.pid
                    fi

                    # Миграции (если есть БД)
                    python manage.py migrate --noinput || true

                    # Запуск в фоне, чтобы Jenkins не висел
                    nohup python manage.py runserver 0.0.0.0:$APP_PORT > django.log 2>&1 &
                    echo $! > django.pid

                    # Даём секунду подняться и проверяем, что живой
                    sleep 3
                    curl -f http://127.0.0.1:$APP_PORT/ || (echo "Django не поднялся"; cat django.log; exit 1)
                '''
            }
        }
    }

    post {
        failure {
            sh 'cat django.log || true'
        }
    }
}