# ⚙️ Engineering Knowledge Assistant

> An AI-powered automation engineering knowledge assistant using Agentic RAG, hybrid retrieval, multimodal document processing, and web-search fallback.

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-Vector_Search-336791)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM_&_Embeddings-412991?logo=openai&logoColor=white)
![Azure](https://img.shields.io/badge/Azure-Blob_Storage-0078D4?logo=microsoftazure&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Orchestration-326CE5?logo=kubernetes&logoColor=white)
![Git](https://img.shields.io/badge/Git-Version_Control-F05032?logo=git&logoColor=white)

---

## 📑 Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Problem Statement](#2-problem-statement)
- [3. Objectives](#3-objectives)
- [4. Key Features](#4-key-features)
- [5. System Architecture](#5-system-architecture)
  - [5.1 Architecture Diagram](#51-architecture-diagram)
  - [5.2 Query Processing Flow](#52-query-processing-flow)
  - [5.3 Document Ingestion](#53-document-ingestion)
- [6. Microservices](#6-microservices)
  - [6.1 Frontend Service](#61-frontend-service)
  - [6.2 Backend Service](#62-backend-service)
  - [6.3 Database Service](#63-database-service)
- [7. Dataset and Data Sources](#7-dataset-and-data-sources)
- [8. AI and RAG Workflow](#8-ai-and-rag-workflow)
- [9. Project Structure](#9-project-structure)
- [10. Prerequisites & Configuration](#10-prerequisites--configuration)
- [11. Run Locally](#11-run-locally)
- [12. Docker & Kubernetes Deployment](#12-docker--kubernetes-deployment)
- [13. Evaluation](#13-evaluation)
- [14. Known Issues & Limitations](#14-known-issues--limitations)
- [15. Team & Contributions](#15-team--contributions)
- [16. Future Improvements](#16-future-improvements)
- [17. Disclaimer](#17-disclaimer)

---

## 1. Project Overview

The **Engineering Knowledge Assistant** is an AI-powered application designed to help users retrieve information from automation engineering documents, workplace safety guidelines, standard operating procedures (SOPs), manuals, and other technical resources through natural-language questions.

The application combines **Retrieval-Augmented Generation (RAG)**, hybrid retrieval, multimodal document processing, and threshold-based agent routing to generate source-grounded answers from an internal engineering knowledge base.

When the internal knowledge base does not contain sufficiently relevant information, the system automatically routes the query to a web-search fallback.

The application is implemented using a **microservices architecture** consisting of Streamlit, FastAPI, and PostgreSQL with pgvector, and is containerized and deployed using Docker and Kubernetes.

## 2. Problem Statement

Automation engineers and technical personnel often rely on information distributed across lengthy engineering documents, workplace safety guidelines, standard operating procedures (SOPs), manuals, and research materials. Manually searching through these documents can be time-consuming, especially when users need specific technical or safety-related information quickly.

Traditional keyword search may also fail to capture the semantic meaning of a user's question or retrieve supporting information contained in document images.

The **Engineering Knowledge Assistant** addresses this problem by providing a centralized, AI-powered interface that allows users to query automation-engineering knowledge using natural language. The system retrieves relevant internal knowledge, generates source-grounded responses, and automatically falls back to web search when the internal knowledge base does not contain sufficiently relevant information.

---

## 3. Objectives

The project aims to:

- Develop an AI-powered knowledge assistant focused on automation engineering and workplace safety.
- Provide natural-language access to information stored across PDF and DOCX technical documents.
- Reduce the time required to manually search engineering documents and SOPs.
- Implement Retrieval-Augmented Generation (RAG) to generate answers grounded in retrieved internal knowledge.
- Combine vector similarity and keyword search through hybrid retrieval.
- Support multimodal knowledge retrieval by processing both document text and extracted images.
- Apply threshold-based routing to automatically select between internal RAG and web-search fallback.
- Design the application using a modular microservices architecture for scalability and maintainability.
- Containerize the application using Docker and deploy it using Kubernetes.
- Evaluate the quality of retrieval, generated answers, and routing behaviour using a structured evaluation dataset.

---

## 4. Key Features

| Feature | Description |
|---|---|
| **Natural-Language Q&A** | Users can ask automation-engineering and safety-related questions through a conversational interface. |
| **Internal RAG** | Relevant document chunks are retrieved and supplied to the LLM to generate source-grounded answers. |
| **Hybrid Retrieval** | Combines dense vector similarity search using pgvector with PostgreSQL full-text keyword search. |
| **Threshold-Based Routing** | The highest retrieval score is compared against a configured threshold to determine whether to use internal RAG or web search. |
| **Web-Search Fallback** | Queries without sufficiently relevant internal knowledge are routed to web search through the Serper API. |
| **Multimodal Retrieval** | Extracted document images are captioned, embedded, and semantically retrieved alongside relevant text. |
| **Source Attribution** | Internal responses display supporting document sources, while fallback responses provide web sources. |
| **Centralized Document Storage** | Original PDF/DOCX documents and extracted images are maintained in Azure Blob Storage. |
| **Document Ingestion Pipeline** | An offline backend workflow parses documents, creates chunks, extracts images, generates captions and embeddings, and stores searchable data. |
| **Conversation History** | The frontend provides session-based chat history for previous conversations. |
| **Microservices Architecture** | Frontend, backend, and database responsibilities are separated into independently containerized services. |
| **Kubernetes Deployment** | Kubernetes manages service discovery, backend replicas, rolling updates, configuration, secrets, persistence, and external access through Ingress. |

---

## 5. System Architecture

The application follows a **microservices architecture** with three primary services:

1. **Frontend Service** — Streamlit-based user interface.
2. **Backend Service** — FastAPI application responsible for retrieval, routing, RAG generation, web-search fallback, and document ingestion.
3. **Database Service** — PostgreSQL with pgvector for document metadata, text chunks, vector embeddings, image captions, and related metadata.

The backend also integrates with external services including **OpenAI**, **Serper API**, and **Azure Blob Storage**.

### 5.1 Architecture Diagram

<img width="1536" height="1024" alt="system_architecture" src="https://github.com/user-attachments/assets/7b003961-9f84-421c-9a74-4505d9586f78" />



### 5.2 Query Processing Flow

When a user submits a question:

1. The Streamlit frontend sends the question to the FastAPI backend through `POST /chat`.
2. The backend validates the question and generates a query embedding.
3. The Retrieval Service performs hybrid retrieval over the internal knowledge base.
4. The highest retrieval score is compared against the configured retrieval threshold.
5. If the score meets the threshold, the **Internal RAG route** is selected.
6. Relevant document images are also retrieved semantically for the internal route.
7. If the score is below the threshold, the query is routed to the **web-search fallback** using Serper.
8. The backend returns the generated answer, sources, relevant images where applicable, and route information to the frontend.

### 5.3 Document Ingestion

Document ingestion is implemented as an **offline backend workflow** rather than a separate microservice.

The ingestion pipeline:

`Azure Blob Storage → Parse PDF/DOCX → Structure-Aware Chunking → Extract Images → Generate Image Captions → Generate Embeddings → PostgreSQL + pgvector`

Original documents and extracted image files are stored centrally in Azure Blob Storage, while searchable metadata, chunks, embeddings, and image-caption information are maintained in PostgreSQL.

---

## 6. Microservices

The system is divided into three primary microservices. Each service has a clearly defined responsibility and is containerized independently, improving modularity, maintainability, and scalability.

### 6.1 Frontend Service

**Technology:** Streamlit

The Frontend Service provides the user-facing conversational interface for the Engineering Knowledge Assistant.

Its responsibilities include:

- Accepting natural-language questions from users.
- Sending questions to the backend through the REST API using `POST /chat`.
- Displaying generated answers and route information.
- Displaying supporting document or web sources.
- Rendering relevant retrieved images when available.
- Maintaining session-based conversation history.
- Providing user-friendly error messages when the backend is unavailable or a request fails.

The frontend does not perform retrieval, RAG, or database operations directly. All AI and knowledge-processing logic is delegated to the Backend Service.

---

### 6.2 Backend Service

**Technology:** FastAPI

The Backend Service contains the core application and AI logic. It exposes the `/chat` endpoint used by the frontend and coordinates the complete question-answering workflow.

Its main responsibilities include:

- Validating incoming user questions.
- Generating query embeddings using OpenAI.
- Retrieving relevant internal text using hybrid retrieval.
- Retrieving relevant document images using semantic similarity.
- Comparing retrieval confidence against the configured threshold.
- Routing queries between internal RAG and web-search fallback.
- Generating source-grounded responses using an LLM.
- Performing web search through the Serper API when internal information is insufficient.
- Returning answers, sources, images, and routing information to the frontend.
- Running the offline document-ingestion pipeline.

#### Threshold-Based Routing

The backend uses retrieval confidence to determine which information source should answer a query.

```text
User Question
      ↓
Generate Query Embedding
      ↓
Hybrid Retrieval
      ↓
Highest Retrieval Score
      ↓
Compare with Retrieval Threshold
      │
      ├── Score ≥ Threshold → Internal RAG
      │
      └── Score < Threshold → Web Search Fallback
```

### 6.3 Database Service

**Technology:** PostgreSQL + pgvector

The Database Service provides persistent storage and vector-search capabilities for the internal knowledge base.

Its responsibilities include:

- Storing document metadata and processing status.
- Storing document chunks and vector embeddings.
- Storing image captions, embeddings and metadata.
- Supporting vector similarity and full-text search.
- Providing persistent PostgreSQL storage through Kubernetes PVC.

The Database Service is accessed by the Backend Service through the internal Kubernetes `database-service`.

----

## 7. Dataset and Data Sources

### 7.1 Dataset Overview

The Engineering Knowledge Assistant uses a curated document corpus focused on **automation engineering, workplace safety, manufacturing, engineering procedures, and technical knowledge**.

The dataset contains documents in:

- PDF (`.pdf`)
- Microsoft Word (`.docx`)

The corpus contains a combination of:

1. **Publicly available engineering and workplace-safety documents**, including materials obtained from the Workplace Safety and Health Council (WSH Council) in Singapore.
2. **Project-generated documents**, created to provide additional automation-engineering knowledge and technical content for development and testing.

The documents are not used to train a new large language model. Instead, they form the internal knowledge base used by the **Retrieval-Augmented Generation (RAG)** pipeline.

Original documents are maintained centrally in **Azure Blob Storage**. During ingestion, their contents are transformed into searchable text chunks, embeddings, image captions, and metadata stored in PostgreSQL with pgvector.

---

### 7.2 Data Sources

The project uses both real-world and generated data sources to provide sufficient coverage for the automation-engineering knowledge assistant.

| Source Type | Description | Purpose |
|---|---|---|
| **WSH Council Documents** | Publicly available workplace safety and health guidelines relevant to manufacturing, occupational safety, hazards, and engineering practices in Singapore. | Provides real-world and authoritative safety-related knowledge for the internal RAG system. |
| **Other Technical / Research Documents** | Technical or research materials relevant to engineering procedures and automation-related topics. | Expands the internal knowledge base with specialised engineering information. |
| **Project-Generated Documents** | Technical documents created by the project team for automation-engineering topics and system testing. | Provides additional domain-specific knowledge and allows controlled testing of retrieval behaviour. |

The use of both real-world and generated documents supports the project requirement to source or generate suitable data while providing a diverse knowledge base for retrieval and evaluation.

> **Note:** External documents remain the intellectual property of their respective publishers and authors and are used in this academic project as knowledge sources for retrieval and evaluation.

---

### 7.3 WSH Council Data

A portion of the internal knowledge base is sourced from publicly available materials published by the **Workplace Safety and Health (WSH) Council, Singapore**.

These documents provide practical information related to areas such as:

- Workplace safety and health.
- Manufacturing-industry safety.
- Occupational diseases.
- Combustible-dust hazards.
- Design for safety.
- Common workplace and manufacturing hazards.

These materials are particularly relevant to the project because workplace safety is an important part of automation and manufacturing environments.

The use of real-world WSH materials allows the system to demonstrate retrieval from practical engineering and safety documents rather than relying entirely on generated content.

---

### 7.4 Project-Generated Data

In addition to externally sourced documents, selected documents were generated specifically for this project.

The generated documents provide additional content related to automation engineering, technical procedures, manuals, standards, and other domain-specific topics required by the knowledge assistant.

Generated data is useful for:

- Expanding automation-engineering coverage.
- Creating controlled knowledge for retrieval testing.
- Testing PDF and DOCX ingestion.
- Testing structure-aware chunking.
- Testing source attribution.
- Testing semantic and keyword retrieval.
- Testing questions where the expected source document is known.

Generated documents are processed using the same ingestion and retrieval pipeline as externally sourced documents.

---

### 7.5 Document Ingestion and Processing

Document ingestion is implemented as an offline workflow within the Backend Service.

The ingestion process is:

```text
Azure Blob Storage
        ↓
Load PDF / DOCX
        ↓
Parse Text and Document Structure
        ↓
Structure-Aware Chunking
        ↓
Generate Text Embeddings
        ↓
Extract Document Images
        ↓
Generate Image Captions
        ↓
Generate Caption Embeddings
        ↓
Store Searchable Data in PostgreSQL + pgvector
        ↓
Store Extracted Images in Azure Blob Storage
```
The ingestion pipeline converts unstructured engineering documents into searchable knowledge that can be retrieved by the RAG system.

The database maintains:

Document metadata.
Text chunks.
Chunk metadata.
Vector embeddings.
Image metadata.
Image captions.
Caption embeddings.
References to files stored in Azure Blob Storage.

Azure Blob Storage acts as the centralized file repository for:

Original PDF documents.
Original DOCX documents.
Extracted document images.

-----

## 8. AI and RAG Workflow

The Engineering Knowledge Assistant uses **Retrieval-Augmented Generation (RAG)** to generate responses grounded in the internal engineering knowledge base.

### 8.1 Query Processing

When a user submits a question:

1. The Streamlit frontend sends the question to the FastAPI backend through `POST /chat`.
2. The backend generates an embedding for the user query.
3. The Retrieval Service searches the internal knowledge base.
4. The Agent Service evaluates the retrieval result using the configured score threshold.
5. The query is routed to either **Internal RAG** or **Web Search Fallback**.
6. The generated answer, sources, images, and route information are returned to the frontend.

### 8.2 Hybrid Retrieval

Text retrieval combines:

- **Vector Search** — pgvector compares the query embedding with document-chunk embeddings to find semantically similar content.
- **Keyword Search** — PostgreSQL Full-Text Search (FTS) retrieves content containing relevant keywords and technical terminology.

Combining both approaches improves retrieval for engineering questions containing both semantic meaning and specific technical terms.

### 8.3 Internal RAG

When the retrieved content meets the configured relevance threshold, the system uses the **Internal RAG route**.

Relevant document chunks are provided to the LLM as context for answer generation. The system also performs semantic image retrieval using image-caption embeddings.

The response can include:

- A source-grounded answer
- Supporting document sources
- Relevant document images

### 8.4 Web Search Fallback

If the internal retrieval score is below the configured threshold, the Agent Service routes the question to the **Web Search Fallback**.

The Serper API retrieves relevant web results, which are provided as context to the LLM. The generated response is then returned with its supporting web sources.

### 8.5 Multimodal Retrieval

During document ingestion, extracted images are captioned and converted into embeddings. The captions, embeddings, and image metadata are stored in PostgreSQL, while the actual image files are stored in Azure Blob Storage.

For Internal RAG queries, the system can semantically retrieve relevant images using the query embedding and display them together with the generated answer.

---

## 9. Project Structure

The repository is organised into separate **frontend, backend, database, and deployment components**, supporting modular development and independent containerization of each microservice.

```text
agentic-engineering-knowledge-assistant/
│
├── frontend-service/          # Streamlit user interface
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
│
├── backend-service/           # FastAPI, Agent, RAG and ingestion
│   ├── app/
│   │   ├── agent/
│   │   ├── api/
│   │   ├── chunking/
│   │   ├── ingestion/
│   │   ├── repositories/
│   │   └── retrieval/
│   ├── scripts/
│   ├── Dockerfile
│   └── requirements.txt
│
├── database-service/          # PostgreSQL + pgvector setup
│   ├── migrations/
│   ├── scripts/
│   └── Dockerfile
│
├── kubernetes/                # Kubernetes deployment manifests
│   ├── frontend/
│   ├── backend/
│   ├── database/
│   ├── configmap.yaml
│   ├── secret.example.yaml
│   └── ingress.yaml
│
├── docker-compose.yml
└── README.md

```

Service Separation
| Component            | Responsibility                                                          |
| -------------------- | ----------------------------------------------------------------------- |
| **Frontend Service** | User interface, chat interaction, sources and image display             |
| **Backend Service**  | API, agent routing, retrieval, RAG, web fallback and document ingestion |
| **Database Service** | Persistent metadata, document chunks, embeddings and image metadata     |
| **Kubernetes**       | Deployment, networking, configuration, secrets, scaling and persistence |

This structure keeps the major application components separated, improving modularity, maintainability, and scalability.

## 10. Prerequisites & Configuration

### Prerequisites

Ensure the following tools are installed:

- Python 3.12
- Git
- Docker Desktop
- kubectl
- Minikube

The application also requires credentials for **OpenAI**, **Serper API**, and **Azure Blob Storage**.

### Configuration

Configuration is managed through environment variables:

- **ConfigMap** — non-sensitive settings such as database host, ports, `TOP_K`, retrieval threshold, backend URL and request timeout.
- **Secret** — sensitive values such as database passwords, API keys and Azure credentials.
- **`.env`** — used for local development configuration.

For Kubernetes deployment, create the local Secret from the provided example:

```cmd
copy kubernetes\secret.example.yaml kubernetes\secret.yaml
```

## 11. Run Locally

The three microservices can be run independently during development.

### 11.1 Database Service

Start the PostgreSQL + pgvector database:

```cmd
cd database-service
docker compose up -d
```

Verify that the database container is running:

```cmd
docker ps
```

---

### 11.2 Backend Service

Navigate to the backend:

```cmd
cd backend-service
```

Create and activate a Python virtual environment:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Install the dependencies:

```cmd
pip install -r requirements.txt
```

Ensure the required environment variables are configured, then start the FastAPI backend:

```cmd
uvicorn app.main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Verify the backend health endpoint:

```cmd
curl http://127.0.0.1:8000/health
```

A healthy backend should return a response indicating that the service is running.

---

### 11.3 Frontend Service

Open a new terminal and navigate to the frontend:

```cmd
cd frontend-service
```

Install the required dependencies:

```cmd
pip install -r requirements.txt
```

Start the Streamlit application:

```cmd
streamlit run app.py
```

The frontend will open in the browser and communicate with the FastAPI backend through the configured `BACKEND_URL`.

---

### 11.4 Document Ingestion

Documents are ingested through the offline ingestion script in the Backend Service.

Ensure the database and required external services are configured before running:

```cmd
cd backend-service
.venv\Scripts\activate
```

Run the ingestion script:

```cmd
python -m scripts.ingest_documents
```

The ingestion pipeline reads the source documents, processes text and images, generates embeddings, and stores the searchable knowledge in PostgreSQL + pgvector.

> **Note:** Valid OpenAI, Serper and Azure Blob Storage credentials must be configured before running the complete application. Local `.env` files containing credentials should not be committed to Git.

---

## 12. Docker & Kubernetes Deployment

The Engineering Knowledge Assistant is containerized using **Docker** and deployed using **Kubernetes on Minikube**. Each microservice is deployed independently, allowing the application components to be managed, updated and scaled separately.

### 12.1 Docker Containerization

The application consists of three independently containerized microservices:

| Microservice | Technology | Container Purpose |
|---|---|---|
| **Frontend Service** | Streamlit | Hosts the user interface |
| **Backend Service** | FastAPI | Runs API, Agent/RAG and retrieval logic |
| **Database Service** | PostgreSQL + pgvector | Stores documents, embeddings and metadata |

Each service contains its own Docker configuration and dependencies.

Example image build:

```cmd
docker build -t knowledge-assistant-backend:1.0 backend-service
docker build -t knowledge-assistant-frontend:1.0 frontend-service
```

The deployment images can be tagged and pushed to a container registry so that Kubernetes can pull them when creating Pods.

---

### 12.2 Kubernetes Deployment Architecture

The application is deployed on a local Kubernetes cluster using **Minikube**.

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/ff521c66-72ff-415d-b505-9dbd1a957905" />


The Kubernetes deployment uses:

- **Deployments** to manage application Pods.
- **ReplicaSets** through Deployments to maintain the required number of backend Pods.
- **Services** for stable internal communication between microservices.
- **RollingUpdate** strategy for controlled backend updates.
- **ConfigMap** for non-sensitive application configuration.
- **Secret** for credentials and API keys.
- **PersistentVolumeClaim (PVC)** for PostgreSQL data persistence.
- **NGINX Ingress** to provide a single user-facing entry point.

---

### 12.3 Start the Kubernetes Cluster

Docker Desktop must be running when Minikube uses the Docker driver.

Start Minikube:

```cmd
minikube start
```

Verify the cluster:

```cmd
kubectl get nodes
```

Enable the NGINX Ingress Controller:

```cmd
minikube addons enable ingress
```

Verify that the controller is running:

```cmd
kubectl get pods -n ingress-nginx
```

---

### 12.4 Deploy the Application

Create the Kubernetes configuration and Secret first:

```cmd
kubectl apply -f kubernetes\configmap.yaml
kubectl apply -f kubernetes\secret.yaml
```

Deploy the Database Service:

```cmd
kubectl apply -f kubernetes\database\pvc.yaml
kubectl apply -f kubernetes\database\deployment.yaml
kubectl apply -f kubernetes\database\service.yaml
```

Deploy the Backend Service:

```cmd
kubectl apply -f kubernetes\backend\deployment.yaml
kubectl apply -f kubernetes\backend\service.yaml
```

Deploy the Frontend Service:

```cmd
kubectl apply -f kubernetes\frontend\deployment.yaml
kubectl apply -f kubernetes\frontend\service.yaml
```

Finally, deploy the Ingress:

```cmd
kubectl apply -f kubernetes\ingress.yaml
```

Verify the deployment:

```cmd
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get pvc
kubectl get ingress
```

All application Pods should reach the `Running` state before testing the application.

---

### 12.5 Kubernetes Service Communication

Kubernetes provides internal DNS-based service discovery between the microservices.

```text
User
  │
  ▼
NGINX Ingress
  │
  ▼
Frontend Service
  │
  │ http://backend-service:8000
  ▼
Backend Service
  │
  │ PostgreSQL connection
  ▼
Database Service
```

The frontend communicates with the backend using:

```text
http://backend-service:8000
```

The backend communicates with PostgreSQL through:

```text
database-service:5432
```

This avoids hard-coding Pod IP addresses, which may change whenever Kubernetes replaces a Pod.

---

### 12.6 Backend Replication and Scalability

The Backend Deployment uses multiple replicas.

```yaml
spec:
  replicas: 3
```

Kubernetes creates and manages the corresponding ReplicaSet to maintain the desired number of backend Pods.

The Backend Service provides a stable endpoint in front of these replicas and distributes requests across the available backend Pods.

The deployment can be verified using:

```cmd
kubectl get pods -l app=backend
```

This architecture allows the stateless Backend Service to scale independently from the frontend and database.

---

### 12.7 Rolling Updates

The Backend Deployment uses the Kubernetes **RollingUpdate** deployment strategy.

This allows a new backend version to be introduced gradually instead of terminating all existing Pods at once.

The deployment configuration includes:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1

minReadySeconds: 10
```

- `maxUnavailable: 1` limits how many desired backend Pods may be unavailable during an update.
- `maxSurge: 1` allows Kubernetes to temporarily create one additional Pod during rollout.
- `minReadySeconds: 10` requires a new Pod to remain ready for the configured period before it is considered available.

A deployment update can be monitored using:

```cmd
kubectl rollout status deployment/backend-deployment
```

Deployment history can be viewed using:

```cmd
kubectl rollout history deployment/backend-deployment
```

If a new deployment causes problems, Kubernetes also supports rollback to a previous revision:

```cmd
kubectl rollout undo deployment/backend-deployment
```

---

### 12.8 Configuration and Secret Management

Kubernetes separates application configuration from container images.

**ConfigMap** stores non-sensitive configuration such as:

- Database host and port
- Retrieval settings
- Retrieval score threshold
- Backend service URL
- Request timeout

**Secret** stores sensitive values such as:

- Database password
- OpenAI API key
- Serper API key
- Azure Storage credentials

This allows configuration to be changed without hard-coding credentials into the application source code or Docker images.

---

### 12.9 Persistent Database Storage

PostgreSQL uses a **PersistentVolumeClaim (PVC)** so that database data is stored independently of the database Pod lifecycle.

```text
Database Pod
     │
     ▼
PersistentVolumeClaim
     │
     ▼
PersistentVolume
```

If Kubernetes recreates the PostgreSQL Pod, the replacement Pod can reconnect to the persistent storage rather than relying only on temporary container storage.

Verify the PVC using:

```cmd
kubectl get pvc
```

---

### 12.10 Ingress Access

The application uses **NGINX Ingress** as the external entry point instead of exposing every microservice directly.

The configured local hostname is:

```text
auto-eng.local
```

For the Minikube Docker driver on Windows, start the tunnel when required:

```cmd
minikube tunnel
```

Keep the tunnel terminal running during the application demo.

The application can then be accessed from the browser using:

```text
http://auto-eng.local
```

Only the frontend needs to be exposed to the user. Backend and database communication remains internal to the Kubernetes cluster.

---

### 12.11 Deployment Verification

Useful commands for checking the deployed system are:

```cmd
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get pvc
kubectl get ingress
```

Backend health can also be checked from inside the cluster:

```cmd
kubectl exec deployment/frontend-deployment -- python -c "import requests; print(requests.get('http://backend-service:8000/health').text)"
```

A successful response confirms that the Frontend Service can communicate with the Backend Service through Kubernetes networking.

> **Deployment Scope:** The current Kubernetes deployment uses Minikube for local development and live demonstration. The same containerized microservice design can later be adapted to a managed Kubernetes environment for public cloud deployment.

---

## 12. Docker & Kubernetes Deployment

The Engineering Knowledge Assistant is containerized using **Docker** and deployed using **Kubernetes on Minikube**. Each microservice is packaged as an independent Docker image and published to **Docker Hub**, allowing Kubernetes to pull and deploy the services consistently.

### 12.1 Docker Containerization

The system consists of three independently containerized microservices:

| Microservice | Technology | Purpose |
|---|---|---|
| **Frontend Service** | Streamlit | Provides the conversational user interface |
| **Backend Service** | FastAPI | Handles API requests, retrieval, routing, RAG and web-search fallback |
| **Database Service** | PostgreSQL + pgvector | Stores documents, chunks, embeddings and metadata |

Each microservice has its own Docker image, allowing the services to be built, deployed and updated independently.

### 12.2 Docker Hub Registry

All three application images are published to **Docker Hub** and are referenced by the Kubernetes Deployment manifests.

```text
Source Code
    │
    ▼
Docker Build
    │
    ▼
Docker Images
    │
    ▼
Docker Hub Registry
    │
    ▼
Kubernetes Deployments
    │
    ▼
Application Pods
```

Published images:

```text
chanmyae99/knowledge-assistant-frontend:1.0
chanmyae99/knowledge-assistant-backend:1.0
chanmyae99/knowledge-assistant-database:1.0
```

The images can be built, tagged and published using:

```cmd
docker build -t knowledge-assistant-frontend:1.0 frontend-service
docker tag knowledge-assistant-frontend:1.0 chanmyae99/knowledge-assistant-frontend:1.0
docker push chanmyae99/knowledge-assistant-frontend:1.0
```

```cmd
docker build -t knowledge-assistant-backend:1.0 backend-service
docker tag knowledge-assistant-backend:1.0 chanmyae99/knowledge-assistant-backend:1.0
docker push chanmyae99/knowledge-assistant-backend:1.0
```

```cmd
docker build -t knowledge-assistant-database:1.0 database-service
docker tag knowledge-assistant-database:1.0 chanmyae99/knowledge-assistant-database:1.0
docker push chanmyae99/knowledge-assistant-database:1.0
```

Kubernetes then pulls the published images when creating the application Pods.

For example:

```yaml
containers:
  - name: backend
    image: chanmyae99/knowledge-assistant-backend:1.0
```

This provides a reusable deployment workflow where the same container images can be deployed consistently across Kubernetes environments.

---

### 12.3 Kubernetes Deployment Architecture

The application is deployed on a local Kubernetes cluster using **Minikube**.

![Kubernetes Deployment Architecture](docs/images/kubernetes-deployment.png)

The deployment uses:

- **Deployments and ReplicaSets** to manage application Pods.
- **Kubernetes Services** for stable communication between microservices.
- **3 backend replicas** for scalability and availability.
- **RollingUpdate** for controlled backend updates.
- **ConfigMap** for non-sensitive configuration.
- **Secret** for credentials and API keys.
- **PersistentVolumeClaim (PVC)** for PostgreSQL data persistence.
- **NGINX Ingress** as the user-facing entry point.

---

### 12.4 Start the Kubernetes Cluster

Ensure **Docker Desktop** is running, then start Minikube:

```cmd
minikube start
```

Verify the cluster:

```cmd
kubectl get nodes
```

Enable NGINX Ingress:

```cmd
minikube addons enable ingress
```

Verify the Ingress Controller:

```cmd
kubectl get pods -n ingress-nginx
```

---

### 12.5 Deploy the Application

Apply the application configuration:

```cmd
kubectl apply -f kubernetes\configmap.yaml
kubectl apply -f kubernetes\secret.yaml
```

Deploy the Database Service:

```cmd
kubectl apply -f kubernetes\database\pvc.yaml
kubectl apply -f kubernetes\database\deployment.yaml
kubectl apply -f kubernetes\database\service.yaml
```

Deploy the Backend Service:

```cmd
kubectl apply -f kubernetes\backend\deployment.yaml
kubectl apply -f kubernetes\backend\service.yaml
```

Deploy the Frontend Service:

```cmd
kubectl apply -f kubernetes\frontend\deployment.yaml
kubectl apply -f kubernetes\frontend\service.yaml
```

Deploy the Ingress:

```cmd
kubectl apply -f kubernetes\ingress.yaml
```

Verify the deployment:

```cmd
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get pvc
kubectl get ingress
```

All application Pods should reach the `Running` state before testing the application.

---

### 12.6 Kubernetes Networking

Kubernetes Services provide stable internal communication between the microservices:

```text
User
  │
  ▼
NGINX Ingress
  │
  ▼
Frontend Service
  │
  │ http://backend-service:8000
  ▼
Backend Service
  │
  │ database-service:5432
  ▼
Database Service
```

The frontend and backend therefore communicate using Kubernetes service names rather than temporary Pod IP addresses.

---

### 12.7 Scalability and Rolling Updates

The Backend Service runs with **3 replicas**, allowing Kubernetes to maintain multiple FastAPI Pods behind a single Backend Service.

```yaml
replicas: 3

strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1

minReadySeconds: 10
```

This provides:

- Horizontal backend scaling.
- Load distribution across backend Pods.
- Automatic replacement of failed Pods.
- Controlled application updates with reduced downtime.

Monitor a rollout using:

```cmd
kubectl rollout status deployment/backend-deployment
```

View rollout history:

```cmd
kubectl rollout history deployment/backend-deployment
```

Rollback when required:

```cmd
kubectl rollout undo deployment/backend-deployment
```

---

### 12.8 Configuration, Secrets and Persistence

Kubernetes separates application configuration from the container images:

- **ConfigMap** stores non-sensitive settings such as service URLs, database configuration and retrieval settings.
- **Secret** stores sensitive credentials such as passwords, API keys and Azure Storage credentials.
- **PersistentVolumeClaim (PVC)** provides persistent storage for PostgreSQL so that database data is not tied to the lifecycle of an individual database Pod.

This improves deployment security, portability and maintainability.

---

### 12.9 Ingress Access

NGINX Ingress provides a single entry point to the application.

The configured local hostname is:

```text
auto-eng.local
```

For Minikube using the Docker driver on Windows, run:

```cmd
minikube tunnel
```

Keep the tunnel terminal running during the application demo.

The application can then be accessed through:

```text
http://auto-eng.local
```

Only the frontend is exposed to the user, while the Backend and Database Services remain internal to the Kubernetes cluster.

> **Deployment Scope:** The current deployment uses Minikube for local deployment and live demonstration. The containerized microservice architecture can later be migrated to a managed Kubernetes environment for public cloud deployment.

---

## 13. Evaluation

The RAG system was evaluated using a structured test dataset containing reference answers, expected source documents and expected routing behaviour.

### Evaluation Metrics

The evaluation focused on four key metrics:

| Metric | Score | Purpose |
|---|---:|---|
| **Routing Accuracy** | **1.0000** | Measures whether the system selects the correct Internal RAG or Web Search route |
| **Context Precision** | **0.9351** | Measures how relevant the retrieved context is to the question |
| **Context Recall** | **0.9841** | Measures whether the retrieval system captures the required information |
| **Faithfulness** | **0.9613** | Measures whether generated answers are supported by the retrieved context |

### Results

The system achieved strong performance across all evaluated metrics:

- **100% Routing Accuracy** shows that the threshold-based routing mechanism correctly selected the expected route for the evaluation questions.
- **93.51% Context Precision** indicates that most retrieved information was highly relevant.
- **98.41% Context Recall** shows that the retrieval pipeline successfully captured nearly all required supporting information.
- **96.13% Faithfulness** indicates that generated answers were strongly grounded in the retrieved context.

**RAGAS** was used to evaluate retrieval and generation quality, while **Routing Accuracy** was measured separately against the expected route in the evaluation dataset.

These results demonstrate that the system provides reliable retrieval, effective threshold-based routing and strongly grounded responses for the evaluated test set.

---

## 14. Known Issues & Limitations

The current system is functional, but has several limitations:

- **Knowledge coverage** — Internal RAG responses are limited to the documents currently available in the knowledge base.
- **Threshold dependency** — Routing between Internal RAG and Web Search depends on the configured retrieval-score threshold (`0.30`).
- **External API dependency** — Embeddings and answer generation require OpenAI, while web-search fallback requires Serper API availability.
- **Image retrieval** — Relevant image retrieval depends on the quality of generated image captions and their embeddings.
- **LLM variability** — Generated responses may vary slightly between requests.
- **Local deployment** — Kubernetes is currently deployed using Minikube for development and demonstration rather than a public cloud cluster.
- **Local Ingress** — `auto-eng.local` is accessible only from the configured local machine while Minikube and the required tunnel are running.

> AI-generated responses should be verified against the cited source documents for safety-critical engineering decisions.

---

## 15. Team & Contributions

The Engineering Knowledge Assistant was developed by a three-member team, with each member taking primary responsibility for a major system component while collaborating on integration and testing.

| Team Member | Primary Contribution | Key Responsibilities |
|---|---|---|
| **Chan Myae Aung** | Core Backend & Deployment | FastAPI backend, agent workflow, RAG integration, service integration, Docker containerization, Docker Hub and Kubernetes deployment |
| **Sai Thaw Zin Lynn** | Database & Evaluation | PostgreSQL + pgvector database service, database schema and persistence, RAG evaluation dataset, evaluation metrics and result analysis |
| **Yande** | Frontend | Streamlit frontend, backend API integration, chat interface, conversation history, source display and retrieved image presentation |

All three components were integrated into the final microservices-based application:

```text
Yande                         Chan                         Sai
Frontend Service  ──────►  Backend Service  ──────►  Database Service
                              │
                              └── Deployment              + Evaluation
```

Development was managed using **Git and GitHub**, with team members working on their respective components through feature branches and integrating their work into the final system.

---


## 16. Future Improvements

The current system provides a functional foundation that can be extended in future development. Potential improvements include:

- **Cloud Deployment** — Migrate from local Minikube to a managed Kubernetes platform for public and production-ready access.
- **CI/CD Pipeline** — Automate Docker image building, testing and Kubernetes deployment when new code is merged.
- **Knowledge Base Expansion** — Add more authoritative automation-engineering standards, manuals, SOPs and workplace-safety documents.
- **Retrieval Optimisation** — Further tune hybrid retrieval and the routing threshold using evaluation results.
- **Advanced Reranking** — Introduce a reranking stage to improve the ordering and relevance of retrieved document chunks.
- **Monitoring & Observability** — Add centralized logging, application metrics and Kubernetes monitoring for system health and performance.
- **Security & Access Control** — Introduce authentication and role-based access control for production use.
- **Automated Ingestion** — Replace manual ingestion scripts with an automated pipeline triggered when new documents are added to centralized storage.

---
## 17. Disclaimer

This project was developed for **academic and demonstration purposes**.

The Engineering Knowledge Assistant uses AI-generated responses and may occasionally produce incomplete or inaccurate information. For safety-critical engineering decisions, users should verify information against the **cited source documents, official standards and applicable workplace safety requirements**.

---
