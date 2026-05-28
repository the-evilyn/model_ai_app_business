pipeline {
    agent any

    environment {
      
        IMAGE = "marouamrouji/ia-app"
        TAG = "1.0.${env.BUILD_NUMBER}"
    }

    stages {

        stage('1. Checkout') {
            steps {
                checkout scm
                echo 'Code IA récupéré depuis GitHub ✓'
            }
        }

        stage('1b. Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt --break-system-packages'
            }
        }

        stage('1c. Analyse SonarQube') {
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

        stage('1d. Tests') {
            steps {
                sh 'pytest tests/ -v'
            }
        }

        stage('2. Build Docker Image') {
            steps {
                echo 'Building IA Docker Image...'
                sh "docker build -t ${IMAGE}:${TAG} ."
                sh "docker tag ${IMAGE}:${TAG} ${IMAGE}:latest"
            }
        }

   
        stage('3. Security Scan: Docker Image (Trivy)') {
            steps {
                echo 'Scanning IA Image with Trivy...'
                
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --exit-code 1 --severity CRITICAL ${IMAGE}:${TAG}"
            }
        }

        stage('4. Push Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub',
                    usernameVariable: 'USER',
                    passwordVariable: 'PASS')]) {
                    sh "echo \$PASS | docker login -u \$USER --password-stdin"
                    sh "docker push ${IMAGE}:${TAG}"
                    sh "docker push ${IMAGE}:latest"
                }
            }
        }

        stage('5. Deploy avec Ansible') {
            steps {
         
                sh 'ssh -o StrictHostKeyChecking=no azureuser@74.161.163.110 "ansible-playbook -i ~/ansible/inventory.ini ~/ansible/deploy.yml"'
            }
        }

    }

    post {
        success {
            echo 'Pipeline IA réussi !'
        }
        failure {
            echo 'Pipeline IA échoué — vérifier les logs'
        }
        always {
            cleanWs()
        }
    }
}
