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
                // Pour du Python/Flask ou FastApi généralement utilisé en IA
                sh 'pip install -r requirements.txt || echo "Pas de requirements.txt ou déjà installé"'
            }
        }

        stage('Analyse SonarQube') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        npx sonar-scanner \
                        -Dsonar.projectKey=model-ia \
                        -Dsonar.projectName=model-ia \
                        -Dsonar.sources=.
                    '''
                }
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

        stage('Deploy avec Ansible') {
            steps {
                // Le même playbook magique qui va aussi relancer le pod de l'IA sur Kubernetes
                sh 'ssh -o StrictHostKeyChecking=no azureuser@74.161.163.110 "ansible-playbook -i ~/ansible/inventory.ini ~/ansible/deploy.yml"'
            }
        }

    }

    post {
        success {
            echo 'Pipeline IA réussi !'
        }
        failure {
            echo ' Pipeline IA échoué — vérifier les logs'
        }
        always {
            cleanWs()
        }
    }
}
