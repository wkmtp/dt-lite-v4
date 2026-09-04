# DT-Lite AI Agent Rules
# Agent Context for Phase 0+ Development

## Architecture Rules (ARCH-*)

### ARCH-001
DT-Lite必须基于FIWARE/Eclipse Ditto语义体系。禁止自定义替代Twin核心。

### ARCH-002
AI不能直接访问数据库。必须：
AI → Tool → Service → Database

### ARCH-003
Metadata驱动。禁止硬编码设备模型。所有资产类型必须通过Schema定义。

### ARCH-004
Platform优先原则：
- 禁止先开发智慧园区业务
- 路径：DT-Lite Core Platform → Industry Asset Package → Smart Park Application

### ARCH-005
配置优先原则：
- 禁止硬编码行业
- 采用：Schema + Template + Plugin

### ARCH-006
服务边界：
- Gateway: 统一入口, Token验证, 路由
- Identity: Tenant, User, Role, Permission
- Core: Entity, Asset, Property, Relationship
- Twin: Scene, Model, Binding
- IoT: Device, Protocol, Connection
- Telemetry: 实时数据, 历史数据
- AI: Agent, Tool, RAG
- Application: Page, Widget, Template

## Coding Rules (CODE-*)

### CODE-001 (Python Backend)
- Python 3.11+
- Type Hint 必须
- Async 优先
- Pydantic Schema 定义所有输入输出
- 遵循 FastAPI 最佳实践

### CODE-002 (TypeScript Frontend)
- TypeScript strict mode
- Vue 3 Composition API
- Pinia for state management
- TailwindCSS for styling

### CODE-003
所有API响应格式：
```json
{
  "success": true,
  "data": {...},
  "error": null
}
```

### CODE-004
禁止在Controller/Service层直接操作数据库。必须通过Repository模式。

## Database Rules (DB-*)

### DB-001
所有数据库修改必须通过Alembic Migration完成。禁止直接修改生产数据库。

### DB-002
Migration目录结构：
```
database/migrations/
├── versions/
│   └── xxx_initial.py
├── env.py
└── script.py.mako
```

### DB-003
PostgreSQL数据库设计原则：
- 使用UUID作为主键（可选自增ID辅助）
- 使用TIMESTAMPTZ记录时间
- 使用JSONB存储动态属性
- 外键约束确保数据完整性

## Security Rules (SEC-*)

### SEC-001
所有API必须经过身份验证（JWT Token）。

### SEC-002
敏感信息必须从环境变量读取，禁止硬编码。

### SEC-003
密码必须使用bcrypt哈希存储。

## Testing Rules (TEST-*)

### TEST-001
每个Feature必须有单元测试，覆盖率≥80%。

### TEST-002
测试分层：
- Unit Test (pytest)
- Integration Test
- API Test
- E2E Test

## AI Agent Execution Rules (AI-* )

### AI-001
禁止AI自行修改架构。

### AI-002
禁止AI引入新框架（需经Architecture Review）。

### AI-003
禁止AI直接修改数据库Schema（必须通过Migration）。

## Repository Structure

```
dt-lite-v4/
├── apps/
│   ├── web/           # Vue 3 + Vite
│   └── admin/         # Vue 3 + Vite Admin
├── services/
│   ├── gateway/       # API Gateway
│   ├── identity/      # Identity & Auth
│   ├── core/          # Core Model
│   ├── twin/          # Digital Twin Runtime
│   ├── iot/           # IoT Connectivity
│   ├── telemetry/     # Data Processing
│   ├── ai/            # AI Layer
│   └── application/   # Low-Code App
├── packages/
│   ├── common/        # Shared utilities
│   ├── sdk/           # SDK clients
│   └── schemas/       # JSON Schema definitions
├── plugins/
│   ├── iot/           # IoT plugins
│   ├── industry/      # Industry templates
│   └── ai/            # AI plugins
├── engine/
│   ├── three-runtime/ # Three.js runtime
│   └── scene-editor/  # Scene editor
├── database/
│   ├── migrations/    # Alembic migrations
│   └── seeds/         # Sample data
├── deployment/
│   ├── docker/        # Docker configs
│   └── kubernetes/    # K8s manifests
├── docs/              # Documentation
└── tests/             # Integration tests
```
