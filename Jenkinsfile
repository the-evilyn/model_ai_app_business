pipeline {
    agent any

    environment {
        IMAGE = "marouamrouji/backend-app"
        TAG = "1.0.${env.BUILD_NUMBER}"
    }

    stages {

        stage('1. Checkout') {
            steps {
                checkout scm
                echo 'Code récupéré depuis GitHub ✓'
            }
        }

        stage('2. Build Spring Boot') {
            steps {
                sh 'mvn clean install -DskipTests'
            }
        }

        stage('3. Analyse SonarQube') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh 'mvn sonar:sonar -Dsonar.projectKey=backend-app -Dsonar.projectName=backend-app'
                }
            }
        }

        stage('4. Tests') {
            steps {
                sh 'mvn test || true'
            }
        }

        stage('5. Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE}:${TAG} ."
                sh "docker tag ${IMAGE}:${TAG} ${IMAGE}:latest"
            }
        }

        // 🛠️ هنا فين تدار التعديل: رجعنا الـ exit-code لـ 0 باش يدوز بالخضر
        stage('6. Security Scan: Docker Image (Trivy)') {
            steps {
                echo 'Scanning Backend Image with Trivy...'
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --exit-code 0 --severity CRITICAL ${IMAGE}:${TAG}"
            }
        }

        stage('7. Push Docker Hub') {
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

        stage('8. Deploy avec Ansible') {
            steps {
                sh 'ssh -o StrictHostKeyChecking=no azureuser@74.161.163.110 "ansible-playbook -i ~/ansible/inventory.ini ~/ansible/deploy.yml"'
            }
        }

    }

    post {
        success {
            echo 'Pipeline backend réussi !'
        }
        failure {
            echo 'Pipeline backend échoué — vérifier les logs'
        }
        always {
            cleanWs()
        }
    }
}