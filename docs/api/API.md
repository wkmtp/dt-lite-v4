# DT-Lite V4.0 API Specification

## Overview

All API endpoints follow REST conventions and return standardized responses.

## Base URL

```
http://localhost:8000/api/v1
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid input parameters",
    "details": {}
  }
}
```

## Authentication

All API endpoints (except health checks) require JWT authentication.

```
Authorization: Bearer <token>
```

## Endpoints

### Gateway Service (:8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Service info |
| GET | /health | Health check |
| GET | /api/v1/health | API health check |

### Identity Service (:8001)

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/tenants | List tenants |
| POST | /api/v1/tenants | Create tenant |
| GET | /api/v1/users | List users |
| POST | /api/v1/users | Create user |

### Core Service (:8002)

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/entities | List entities |
| POST | /api/v1/entities | Create entity |
| GET | /api/v1/assets | List assets |
| POST | /api/v1/assets | Create asset |

## Versioning

API version is included in the URL path (`/api/v1/`).
