pipeline {
    agent any

    environment {
        DOCKER_HUB_USER = 'marouamrouji'
        IMAGE_NAME      = 'ia-app' // Nom de ton image pour la partie IA
        IMAGE_TAG       = "1.0.${BUILD_NUMBER}"
        REGISTRY_CRED   = 'docker-hub-credentials' // Ton ID de credentials Jenkins
    }

    stages {
        stage('1. Checkout SCM') {
            steps {
                cleanWs() // Nettoyage complet pour éviter les anciens fichiers
                checkout scm
                echo "✅ Code du projet IA récupéré avec succès"
            }
        }

        stage('2. Analyse SonarQube') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    // Utilisation du sonar-scanner générique (adapté pour Python/JS/IA, pas de Maven ici)
                    sh 'npx sonar-scanner -Dsonar.projectKey=ia-app -Dsonar.projectName=ia-app -Dsonar.sources=. -Dsonar.qualitygate.wait=false'
                }
            }
        }

        stage('3. Security Scan (Trivy fs)') {
            steps {
                echo "🔍 Scanning filesystem specifications with Trivy..."
                // Utilisation de Trivy via Docker pour scanner les fichiers et dépendances (requirements.txt, etc.)
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ${WORKSPACE}:/apps aquasec/trivy fs /apps --severity HIGH,CRITICAL --exit-code 0"
            }
        }

        stage('4. Build Docker Image') {
            steps {
                echo "📦 Building IA Docker Image..."
                sh "docker build --no-cache -t ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('5. Security Scan (Trivy Image)') {
            steps {
                echo "🛡️ Scanning IA Docker Image with Trivy..."
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
                echo "🚀 Déploiement de l'application IA avec Ansible..."
                // Appel de ton fichier deploy.yml unique qui gère l'orchestration sur ton serveur Azure
                sh "ssh -o StrictHostKeyChecking=no azureuser@74.161.163.110 'ansible-playbook -i ~/ansible/inventory.ini ~/ansible/deploy.yml --extra-vars \"image_tag=${IMAGE_TAG}\"'"
            }
        }
    }

    post {
        always {
            cleanWs() // Nettoyage de l'espace de travail à la fin
        }
    }
}
