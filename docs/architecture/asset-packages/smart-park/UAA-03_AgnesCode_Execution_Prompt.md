# DT-Lite V4.0 UAA-03 — Point, Mapping & Capability
## AgnesCode Independent Execution Prompt

**Parent Contract:** Universal Asset Assembly Contract v1.0  
**Status:** Frozen Scope  
**Execution Mode:** Strict Engineering

---

# AgnesCode Common Execution Rules

Parent Contract: DT-Lite V4.0 Universal Asset Assembly Contract v1.0

必须遵守：

1. API → Application Service → Repository → SQLAlchemy ORM → PostgreSQL。
2. Controller 不得承载业务规则。
3. Universal Contract 是最高优先级冻结边界。
4. 不得加入 Park/Factory mandatory field 到 Universal Contract。
5. PointSemantic / Point 与 Protocol Mapping 严格分离。
6. Capability 与 Connector/Plugin Implementation 严格分离。
7. BIM/GIS/3D ModelObject 不能成为 Asset 唯一业务身份。
8. Dashboard 与 LargeScreen 必须是独立对象。
9. ExternalObject 不得替代 Universal Ontology。
10. AI 必须经过 Tool → Capability → Permission → Safety → Audit。
11. Package 不得直接修改 Core DB。
12. Smart Factory 不得重新实现 Assembly Engine。
13. 不得用硬编码行业脚本替代 Zero-Code Assembly Engine。
14. 所有新增代码必须有自动化测试。
15. 不得通过削弱 Contract 约束让测试通过。
16. 发现架构冲突必须 STOP，并输出 Architecture Conflict Report。

固定流程：

Audit
→ Design Lock
→ Implement
→ Test
→ Architecture Check
→ Acceptance


---

## 1. Task Objective

实现 PointSemantic、Point、PointMapping、CapabilityContract、Capability。

实现 Semantic Point 与协议映射的严格分离。

使用 BACnet、Modbus、OPC UA Mock 验证同一 Semantic Point 可以复用不同 Mapping。

---

## 2. Pre-Implementation Audit

编码前必须先输出：

```text
PRE_IMPLEMENTATION_AUDIT
```

必须包含：

```text
Current State
Existing Implementation
Gap Analysis
Files To Change
Files Not To Change
Architecture Risks
Test Plan
Acceptance Plan
```

必须检查当前 Core、Service、Repository、ORM、Migration、API、Tests 以及已有 UAA 实现。

---

## 3. Design Lock

编码前必须明确：

```text
Objects
Fields
References
Lifecycle
State Machine
Schemas
Domain Models
Application Services
Repositories
ORM Models
Migrations
APIs
Tests
```

不得无记录扩大 Scope。

---

## 4. Implementation

遵循：

```text
API
 ↓
Application Service
 ↓
Repository
 ↓
SQLAlchemy ORM
 ↓
PostgreSQL
```

禁止：

```text
Controller → DB
Service → direct SQLAlchemy query bypassing Repository
Package → direct Core DB mutation
AI Agent → DB
AI Agent → Connector
```

---

## 5. Test Requirements

按适用范围实现：

```text
Unit Test
Schema Test
Reference Test
Lifecycle Test
State Machine Test
Architecture Boundary Test
Integration Test
Regression Test
Golden Test
```

必须覆盖失败路径。

不得通过降低 Contract 校验强度让测试通过。

---

## 6. Acceptance Criteria

[ ] PointSemantic 无协议地址
[ ] Point 无协议地址
[ ] PointMapping 保存外部映射
[ ] 同一 Semantic 支持多协议
[ ] Capability I/O Schema 完整
[ ] Preconditions/Error/Retry/Idempotency/Audit 完整
[ ] 控制能力缺 Permission/Safety 时拒绝发布
[ ] Point/Capability Gate PASS

---

## 7. Architecture Gate

完成后逐项检查：

```text
[ ] Contract boundary preserved
[ ] Industry neutrality preserved
[ ] Point / Mapping separation preserved
[ ] Capability / Implementation separation preserved
[ ] External isolation preserved
[ ] BIM/GIS identity boundary preserved
[ ] Dashboard / LargeScreen separation preserved
[ ] AI security chain preserved
[ ] Core / Package boundary preserved
[ ] Service / Repository boundary preserved
[ ] No undocumented hard-coded business rule
```

任一 P0 FAIL：

```text
Status = NOT READY
```

不得声明 COMPLETE。

---

## 8. Final Report

必须输出：

```text
Task:
Status:

Pre-Implementation Audit:
PASS / FAIL

Changed Files:
- ...

New Files:
- ...

Objects:
- ...

Fields:
- ...

References:
- ...

Lifecycle:
- ...

State Machine:
- ...

Schemas:
- ...

APIs:
- ...

Migrations:
- ...

Tests:
- total:
- passed:
- failed:
- skipped:

Architecture Boundary:
PASS / FAIL

Contract Compatibility:
PASS / FAIL

Acceptance:
PASS / FAIL

Known Limitations:
- ...

Architecture Conflicts:
- ...

Next Task:
...
```

禁止使用：

```text
基本完成
功能可用
大体通过
```

代替明确的 PASS / FAIL。
