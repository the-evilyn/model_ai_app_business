pipeline {
    agent any
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
                sh 'pytest tests/ -v'
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t model-ia .'
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
