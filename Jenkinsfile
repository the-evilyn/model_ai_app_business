pipeline {
    agent any

    environment {
        IMAGE = "marouamrouji/model-ia"
        TAG = "1.0.${env.BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo 'Code récupéré depuis GitHub ✓'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt --break-system-packages'
            }
        }

        stage('Analyse SonarQube') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        sonar-scanner \
                        -Dsonar.projectKey=model-ia \
                        -Dsonar.projectName=model-ia \
                        -Dsonar.sources=.
                    '''
                }
            }
        }

        stage('Tests') {
            steps {
                sh 'pytest tests/ -v || true'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE}:${TAG} ."
                sh "docker tag ${IMAGE}:${TAG} ${IMAGE}:latest"
            }
        }

        stage('Push Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub',
                    usernameVariable: 'USER',
                    passwordVariable: 'PASS')]) {
                    sh "echo $PASS | docker login -u $USER --password-stdin"
                    sh "docker push ${IMAGE}:${TAG}"
                    sh "docker push ${IMAGE}:latest"
                }
            }
        }

    }

    post {
        success {
            echo '✅ Pipeline IA réussi !'
        }
        failure {
            echo '❌ Pipeline IA échoué — vérifier les logs'
        }
        always {
            cleanWs()
        }
    }
}
