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

- [Project Overview](#1-project-overview)
  - [Problem Statement](#2-problem-statement)
  - [Objectives](#3-objectives)
  - [Key Features](#4-key-features)
- [System Architecture](#5-system-architecture)
  - [Microservices](#6-microservices)
  - [Dataset and Data Sources](#7-dataset-and-data-sources)
  - [AI and RAG Workflow](#8-ai-and-rag-workflow)
- [Project Setup](#9-project-structure)
  - [Prerequisites](#10-prerequisites)
  - [Configuration](#11-configuration)
  - [Local Development](#12-local-development)
  - [Docker Deployment](#13-docker-deployment)
  - [Kubernetes Deployment](#14-kubernetes-deployment)
- [Using the Application](#15-using-the-application)
- [Evaluation](#16-evaluation)
- [Known Issues and Limitations](#17-known-issues-and-limitations)
- [Team](#18-team)

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
