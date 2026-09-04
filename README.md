# DT-Lite v4.0 - AI Native Low-Code Digital Twin Platform

**数字孪生应用平台 | Digital Twin Application Platform**

## Architecture Overview

```
DT-Lite Architecture
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Apps                          │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │   Web App    │  │  Admin App   │  Vue 3 + TypeScript   │
│  │   (:3000)    │  │   (:3001)    │                       │
│  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Gateway Service (:8000)                    │
│              API Gateway / Token Validation                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Microservices                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Identity │ │  Core   │ │  Twin   │ │   IoT   │          │
│  │ (:8001) │ │ (:8002) │ │ (:8003) │ │ (:8004) │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐         │
│  │Telemetry│ │    AI    │ │Applicantn│ │Plugins  │         │
│  │ (:8005) │ │ (:8006)  │ │ (:8007)  │ │         │         │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  PostgreSQL 16 | TimescaleDB | Redis 7 | MinIO | EMQX      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd dt-lite-v4

# 2. Copy environment variables
cp .env.example .env

# 3. Start all services
make dev

# 4. Access applications
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## Development Commands

```bash
make install      # Install dependencies
make dev          # Start development environment
make test         # Run tests
make build        # Build for production
make clean        # Clean build artifacts
make db-migrate   # Run database migrations
make db-seed      # Seed database with sample data
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Gateway | 8000 | API Gateway & Authentication |
| Identity | 8001 | Tenant, User, Role, Permission |
| Core | 8002 | Entity, Asset, Property |
| Twin | 8003 | Scene, Model, Binding |
| IoT | 8004 | Device, Protocol, Connection |
| Telemetry | 8005 | Real-time & Historical Data |
| AI | 8006 | Agent, Tool, RAG |
| Application | 8007 | Page, Widget, Template |

## Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| PostgreSQL | 5432 | Relational Database |
| TimescaleDB | 5433 | Time-series Data |
| Redis | 6379 | Cache & Session |
| MinIO | 9000 | Object Storage |
| EMQX MQTT | 1883 | IoT Messages |
| EMQX Dashboard | 18083 | MQTT Management |

## Documentation

- [Architecture Specification](../docs/architecture/ARCHITECTURE.md)
- [API Reference](../docs/api/API.md)
- [Developer Guide](../docs/guides/DEVELOPER_GUIDE.md)

## License

MIT License
