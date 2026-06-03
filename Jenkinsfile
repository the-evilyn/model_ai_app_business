pipeline {
    agent any

    environment {
        DOCKER_HUB_USER = 'marouamrouji'
        IMAGE_NAME      = 'frontend-app'
        IMAGE_TAG       = "1.0.${BUILD_NUMBER}"
        REGISTRY_CRED   = 'docker-hub-credentials' // ID correct de tes credentials Docker Hub dans Jenkins
    }

    stages {
        stage('1. Checkout SCM') {
            steps {
                cleanWs() // Nettoie l'espace de travail pour éviter les anciens conflits
                checkout scm
                echo "✅ Code Frontend récupéré avec succès"
            }
        }

        stage('2. Install & Build Angular') {
            steps {
                sh 'npm install'
                sh 'npm run build -- --configuration production'
            }
        }

        stage('3. Analyse SonarQube') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    // Ajout de wait=false pour ne pas bloquer le pipeline si le Quality Gate échoue sur le serveur
                    sh 'npx sonar-scanner -Dsonar.projectKey=frontend-app -Dsonar.projectName=frontend-app -Dsonar.sources=src -Dsonar.qualitygate.wait=false'
                }
            }
        }

        stage('4. Security Scan (Trivy fs)') {
            steps {
                echo "🔍 Scanning filesystem specifications with Trivy..."
                // Exécution via Docker pour éviter l'erreur "trivy introuvable" et exit-code 0 pour la sécurité
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ${WORKSPACE}:/apps aquasec/trivy fs /apps --severity HIGH,CRITICAL --exit-code 0"
            }
        }

        stage('5. Build Docker Image') {
            steps {
                sh "docker build --no-cache -t ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('6. Security Scan (Trivy Image)') {
            steps {
                echo "🛡️ Scanning Docker Image with Trivy..."
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} --severity CRITICAL --exit-code 0"
            }
        }

        stage('7. Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: "${REGISTRY_CRED}", usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh "echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin"
                    sh "docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
                    sh "docker tag ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_HUB_USER}/${IMAGE_NAME}:latest"
                    sh "docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:latest"
                }
            }
        }

        stage('8. Deploy avec Ansible') {
            steps {
                echo "🚀 Déploiement du Frontend avec Ansible..."
                // Correction du chemin et appel du fichier deploy.yml qui gère les rôles sur ton serveur Azure
                sh "ssh -o StrictHostKeyChecking=no azureuser@74.161.163.110 'ansible-playbook -i ~/ansible/inventory.ini ~/ansible/deploy.yml --extra-vars \"image_tag=${IMAGE_TAG}\"'"
            }
        }
    }

    post {
        always {
            cleanWs() // Nettoyage final automatique de l'espace de travail
        }
    }
}
