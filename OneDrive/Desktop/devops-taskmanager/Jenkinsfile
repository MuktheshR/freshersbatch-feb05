pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    triggers {
        githubPush()
    }

    environment {
        // TODO: replace both values before the first run.
        DOCKERHUB_USER = 'your-dockerhub-username'
        APP_SERVER     = 'ubuntu@<APP_EC2_PRIVATE_IP>'
        DEPLOY_DIR     = '/opt/taskmgr'
        BACKEND_IMAGE  = "${DOCKERHUB_USER}/taskmgr-backend"
        FRONTEND_IMAGE = "${DOCKERHUB_USER}/taskmgr-frontend"
        TRIVY_IMAGE    = 'aquasec/trivy:0.58.1'
    }

    stages {
        stage('Prepare') {
            steps {
                script {
                    def shortSha = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${shortSha}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} (${shortSha})"
                }
                sh 'docker version && docker compose version'
            }
        }

        stage('Backend: Lint & Unit Tests') {
            steps {
                sh '''
                    docker build --target test -t taskmgr-backend:test-${BUILD_NUMBER} backend
                    mkdir -p reports
                    docker run --rm -u "$(id -u):$(id -g)" \
                        -v "$WORKSPACE/reports:/reports" \
                        taskmgr-backend:test-${BUILD_NUMBER} \
                        sh -c "flake8 app tests && python -m pytest -v -p no:cacheprovider --junitxml=/reports/backend-junit.xml"
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/*.xml'
                }
            }
        }

        stage('Build Images') {
            parallel {
                stage('Backend') {
                    steps {
                        sh 'docker build --target runtime -t ${BACKEND_IMAGE}:${IMAGE_TAG} -t ${BACKEND_IMAGE}:latest backend'
                    }
                }
                stage('Frontend') {
                    steps {
                        sh 'docker build -t ${FRONTEND_IMAGE}:${IMAGE_TAG} -t ${FRONTEND_IMAGE}:latest frontend'
                    }
                }
            }
        }

        stage('Image Scan (Trivy)') {
            steps {
                // --exit-code 0 reports only; switch to 1 to fail the build on HIGH/CRITICAL findings.
                sh '''
                    for img in ${BACKEND_IMAGE}:${IMAGE_TAG} ${FRONTEND_IMAGE}:${IMAGE_TAG}; do
                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            -v trivy-cache:/root/.cache/ \
                            ${TRIVY_IMAGE} image --no-progress --ignore-unfixed \
                            --severity HIGH,CRITICAL --exit-code 0 "$img"
                    done
                '''
            }
        }

        stage('Push Images') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        docker push ${BACKEND_IMAGE}:${IMAGE_TAG}
                        docker push ${BACKEND_IMAGE}:latest
                        docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                        docker push ${FRONTEND_IMAGE}:latest
                    '''
                }
            }
        }

        stage('Deploy to App Server') {
            steps {
                sshagent(credentials: ['app-server-ssh']) {
                    sh '''
                        SSH_OPTS="-o StrictHostKeyChecking=accept-new"
                        ssh $SSH_OPTS ${APP_SERVER} "mkdir -p ${DEPLOY_DIR}/db"
                        scp $SSH_OPTS docker-compose.yml ${APP_SERVER}:${DEPLOY_DIR}/docker-compose.yml
                        scp $SSH_OPTS db/init.sql ${APP_SERVER}:${DEPLOY_DIR}/db/init.sql
                        ssh $SSH_OPTS ${APP_SERVER} "
                            set -e
                            cd ${DEPLOY_DIR}
                            export DOCKERHUB_USER=${DOCKERHUB_USER} IMAGE_TAG=${IMAGE_TAG}
                            docker compose pull backend frontend
                            docker compose up -d --remove-orphans
                            echo ${IMAGE_TAG} > .deployed_tag
                            docker image prune -f
                        "
                    '''
                }
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    APP_HOST="${APP_SERVER#*@}"
                    for i in $(seq 1 12); do
                        if curl -fsS "http://${APP_HOST}/api/health"; then
                            echo; echo "Smoke test passed"; exit 0
                        fi
                        echo "Waiting for app... ($i/12)"; sleep 5
                    done
                    echo "Smoke test failed"; exit 1
                '''
            }
        }
    }

    post {
        always {
            sh '''
                docker logout || true
                docker rmi taskmgr-backend:test-${BUILD_NUMBER} || true
                docker image prune -f || true
            '''
        }
        success {
            echo "Deployed ${env.IMAGE_TAG} to ${env.APP_SERVER}"
        }
        failure {
            echo 'Pipeline failed - check the stage logs above.'
        }
    }
}
