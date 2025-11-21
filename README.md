# 🎙️ Voice Authentication API (FastAPI + WavLM)

This project provides a Voice Authentication microservice. It allows users to:
1.  **Register** their voice ("My voice is my ID").
2.  **Verify** their identity by speaking the phrase again.

It uses **Microsoft's WavLM** model via the `verifyvoice` library for state-of-the-art speaker verification.

## ⚡ Quick Start (Docker)

The easiest way to run this is with Docker. It includes the database and the API.

### Prerequisites
* Docker & Docker Compose

### 1. Run with Docker Compose
Create a `docker-compose.yml` file (content below) and run:

```bash
docker-compose up --build