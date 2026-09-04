# AGENTS.md - AI Agent Rules

This file defines the rules that AI Coding Agents must follow when developing DT-Lite V4.0.

## Core Principles

1. **Platform First**: Never develop industry-specific features before the platform is stable
2. **Configuration First**: All features must be configurable via Schema/Template/Plugin
3. **Open Source First**: Reuse existing mature solutions (Three.js, EMQX, ThingsBoard, PostgreSQL, etc.)

## Architecture Constraints

- Do NOT modify the service boundaries defined in AGENTS.md
- Do NOT introduce new frameworks without review
- Do NOT modify database schemas directly - use Alembic migrations
- All API responses must follow the standard format: `{"success": bool, "data": any, "error": str}`

## Code Style

### Python (Backend)
- Python 3.11+ required
- Use type hints on all functions
- Use Pydantic v2 for request/response models
- Use async/await for I/O operations
- Follow PEP 8 style guide

### TypeScript (Frontend)
- TypeScript strict mode enabled
- Use Vue 3 Composition API (script setup)
- Use Pinia for state management
- Use TailwindCSS for styling

## Database Rules

- All migrations go in `database/migrations/`
- Use UUID as primary key for main entities
- Use TIMESTAMPTZ for timestamps
- Use JSONB for flexible attributes

## Testing Requirements

- Unit tests for all services (pytest)
- Integration tests for API endpoints
- Minimum 80% code coverage

## Security Rules

- All API endpoints require authentication
- Passwords must be hashed with bcrypt
- Secrets from environment variables only
- CORS configuration in Gateway

## AI Agent Workflow

When receiving a task:
1. Read this file first
2. Understand the service boundary you're working in
3. Create migration if needed
4. Write tests first (TDD)
5. Implement the feature
6. Run tests to verify
