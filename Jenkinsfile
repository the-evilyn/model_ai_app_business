pipeline {
    agent any

    environment {
        DOCKER_HUB_USER = 'marouamrouji'
        IMAGE_NAME      = 'ia-chatbot-app'
        IMAGE_TAG       = "1.0.${BUILD_NUMBER}"
        REGISTRY_CRED   = 'docker-hub-credentials' // Ton ID de credentials Docker Hub dans Jenkins
    }

    stages {
        stage('1. Checkout SCM') {
            steps {
                cleanWs() // Nettoyage de l'espace de travail
                checkout scm
                echo "✅ Code IA Chatbot récupéré avec succès"
            }
        }

        stage('2. Analyse SonarQube') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    echo "🦊 Exécution de SonarQube Scanner via Docker pour Python..."
                    // On utilise le scanner en conteneur pour éviter les conflits de version de Node.js sur le serveur
                    sh """
                        docker run --rm \
                        -e SONAR_HOST_URL=\${SONAR_HOST_URL} \
                        -e SONAR_TOKEN=\${SONAR_AUTH_TOKEN} \
                        -v \${WORKSPACE}:/usr/src \
                        sonarsource/sonar-scanner-cli \
                        -Dsonar.projectKey=ia-chatbot-app \
                        -Dsonar.projectName=ia-chatbot-app \
                        -Dsonar.sources=. \
                        -Dsonar.qualitygate.wait=false
                    """
                }
            }
        }

        stage('3. Security Scan (Trivy fs)') {
            steps {
                echo "🔍 Analyse de sécurité du code source avec Trivy..."
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ${WORKSPACE}:/apps aquasec/trivy fs /apps --severity HIGH,CRITICAL --exit-code 0"
            }
        }

        stage('4. Build Docker Image') {
            steps {
                echo "📦 Construction de l'image Docker Python (FastAPI)..."
                sh "docker build --no-cache -t ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('5. Security Scan (Trivy Image)') {
            steps {
                echo "🛡️ Analyse de l'image Docker finale..."
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} --severity CRITICAL --exit-code 0"
            }
        }

        stage('6. Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: "${REGISTRY_CRED}", usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh "echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin"
                    sh "docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
                    sh "docker tag ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_HUB_USER}/${IMAGE_NAME}:latest"
                    sh "docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:latest"
                }
            }
        }

        stage('7. Deploy avec Ansible') {
            steps {
                echo "🚀 Déploiement de l'application IA sur le serveur Azure..."
                sh "ssh -o StrictHostKeyChecking=no azureuser@74.161.163.110 'ansible-playbook -i ~/ansible/inventory.ini ~/ansible/deploy.yml --extra-vars \"image_tag=${IMAGE_TAG}\"'"
            }
        }
    }

    post {
        always {
            cleanWs() // Nettoyage automatique pour laisser le serveur propre
        }
    }
}
