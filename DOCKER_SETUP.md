# Docker Setup Guide

## Local Development

For local development, the app runs on **port 8080** to avoid conflicts:

```bash
docker-compose up --build
```

Access the application at: **http://localhost:8080**

## Production Deployment

For production, use the `docker-compose.prod.yaml` override to run on **port 80**:

```bash
docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

Access the application at: **http://localhost** or your domain

## Quick Commands

### Stop all containers
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### Rebuild specific service
```bash
docker-compose up --build <service-name>
```

## Port Mappings

- **Frontend (local)**: 8080:80
- **Frontend (prod)**: 80:80
- **Backend**: 8008 (internal only)
- **MongoDB**: 27017 (internal only)

