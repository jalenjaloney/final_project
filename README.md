# Flask GIF Upload Service ![Build Status](https://github.com/jalenjaloney/flask-on-docker/actions/workflows/main.yml/badge.svg)

## Overview
This repository contains a Dockerized Flask web application that allows users to upload GIFs and view them in the browser. The application is served behind Nginx and uses Docker volumes for persistent media storage.

## Demo

Below is a demonstration of:

- Running the application
- Uploading an image
- Viewing the uploaded image

![Application Demo](flask-on-docker-demo.gif)

---

## Architecture

- **Flask** – Web application and upload handling
- **Nginx** – Reverse proxy and static/media serving
- **Docker Compose** – Multi-container orchestration
- **PostgreSQL** (if applicable) – Database persistence
- **Docker Volumes** – Persistent media storage
- **GitHub Actions** – Continuous Integration

---

## Build Instructions

### 1. Clone the repository

```bash
git clone https://github.com/jalenjaloney/flask-on-docker.git
cd yourrepo
```
### 2. Build and start services (Development)

```bash
docker compose up --build
```

### 3. Access the application

Open: `http://localhost:1079`







