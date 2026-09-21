# DT-Lite V4.0 开发组详细工作指令 —— Phase 0 & Phase 1

> **基线**：Universal Asset Assembly Contract v1.0 (FROZEN ⛔)
> **生效时间**：2026-09-16 10:15
> **适用对象**：全体开发组成员 (Platform, Industry, QA, DevOps)
> **执行周期**：Phase 0 (Week 1, Sep 16-22) + Phase 1 (Week 2-3, Sep 23 - Oct 6)

---

## 🎯 核心原则（全员必读、必守）

| 原则 | 说明 | 违规后果 |
|------|------|----------|
| **Contract First** | 所有代码变更必须先通过 `contract-diff` 验证，Universal Contract v1.0 **零修改** | PR 被阻断，需 Architecture Conflict Report |
| **Package Boundary** | Industry Package 只消费 Core Contracts (via SDK)，**禁止**直接操作 Core DB、部署基建 | CI 扫描失败，代码不得合并 |
| **Zero-Code First** | 新业务功能优先通过 Assembly Engine + Studio Tools 实现，**禁止**硬编码业务逻辑 | Code Review 不通过 |
| **Test Mandatory** | 每个新增/修改功能必须有单测 (≥80%) + 集成测 (≥70%) | CI Gate 失败 |
| **Docs as Code** | 文档与代码同仓库、同 PR、同版本，Runbook 必须随功能同步更新 | 发布检查清单不通过 |

---

## 📋 Phase 0: 基线落地 (Week 1, Sep 16-22) —— 立即执行

### 🔴 P0-01: Git 基线标记与分支保护 (Day 1, **今天完成**)

| 任务 | 负责人 | 具体命令/操作 | 验收标准 |
|------|--------|--------------|----------|
| **打标冻结版本** | Platform Lead | ```bash<br>git checkout main<br>git pull origin main<br>git tag -a v4.0.0-uaa-freeze -m "Universal Asset Assembly Contract v1.0 Frozen - 337 tests pass, 14 gates pass, semantic diff=0"<br>git push origin v4.0.0-uaa-freeze<br>``` | Tag 存在于远程，`git tag -l v4.0.0-uaa-freeze` 可见 |
| **创建保护分支** | Platform Lead | ```bash<br>git checkout -b release/uaa-v1.0-frozen v4.0.0-uaa-freeze<br>git push origin release/uaa-v1.0-frozen<br>```<br>然后在 GitHub/GitLab 配置：<br>- 保护分支 `release/uaa-v1.0-frozen`<br>- 必须通过 CI (包括 contract-diff)<br>- 必须 1+ Code Review<br>- 禁止 force push | 分支存在，保护规则生效，尝试直接 push 被拒绝 |
| **更新 main 分支保护** | Platform Lead | 在 main 分支保护规则中添加：<br>- 必须通过 `contract-diff` job<br>- 必须通过 `arch-scan` job<br>- 禁止绕过 CI 合并 | 向 main 提交不通过 contract-diff 的 PR 被自动阻断 |

### 🔴 P0-02: 文档归档与制品注册 (Day 1-2)

| 任务 | 负责人 | 具体操作 | 验收标准 |
|------|--------|----------|----------|
| **Freeze Report 归档只读** | Architecture Lead | 1. 确认 `docs/architecture/freeze/ARCHITECTURE_FREEZE_REPORT_v1.0.md` 为最终版<br>2. Git 历史锁定：`git update-index --assume-unchanged docs/architecture/freeze/ARCHITECTURE_FREEZE_REPORT_v1.0.md`<br>3. 在文档首行添加：`> ⛔ FROZEN - DO NOT MODIFY - Universal Contract v1.0 Baseline` | 文件标记只读，任何修改尝试被 Git 拦截 |
| **11 个 Reports 注册 Agnes Artifacts** | Architecture Team | 使用 `agnes_artifacts__present_artifacts` 依次注册：<br>1. `FINAL_REPORT_UAA-01.md` ~ `FINAL_REPORT_UAA-10.md`<br>2. `ARCHITECTURE_FREEZE_REPORT_v1.0.md`<br>每个 kind=document，dedupe_key=文件名 | Agnes UI 中 11 个 Artifacts 全部显示 ✅ Registered，可下载预览 |

### 🔴 P0-03: Contract Diff CI Job 开发接入 (Day 1-3, **最高优先级**)

| 子任务 | 负责人 | 实现细节 | 完成标准 |
|--------|--------|----------|----------|
| **开发 contract-diff CLI** | Platform Team | 路径：`tools/contract-diff/cli.py`<br>功能：<br>- `contract-diff --baseline universal_v1.0.json --target changed_files.json --output json`<br>- 返回：`{"breaking_changes": [], "additions": [], "deletions": []}`<br>- 非空 breaking_changes → exit code 1 | 单测通过，能准确检测字段增删改、类型变更、enum 变更 |
| **编写基线 Schema 文件** | Architecture Team | 将 6 个 JSON Schema 复制为基线：<br>`packages/schemas/universal/baseline/Asset.json`<br>`packages/schemas/universal/baseline/Point.json`<br>`packages/schemas/universal/baseline/Capability.json`<br>`packages/schemas/universal/baseline/Relationship.json`<br>`packages/schemas/universal/baseline/AssetTemplate.json`<br>`packages/schemas/universal/baseline/CompositeAsset.json` | 文件存在，内容与当前 schemas 完全一致 |
| **新增 GitHub Actions Job** | Platform Team | 编辑 `.github/workflows/ci-comprehensive.yml`：<br>```yaml<br>contract-diff:<br>  name: Contract Diff Gate<br>  runs-on: ubuntu-latest<br>  steps:<br>    - uses: actions/checkout@v4<br>      with:<br>        fetch-depth: 0<br>    - name: Setup Python<br>      uses: actions/setup-python@v5<br>      with:<br>        python-version: '3.11'<br>    - name: Install deps<br>      run: pip install -r tools/contract-diff/requirements.txt<br>    - name: Run Contract Diff<br>      id: diff<br>      run: |<br>        python tools/contract-diff/cli.py \\<br>          --baseline packages/schemas/universal/baseline \\<br>          --target packages/schemas/universal \\<br>          --output json > diff_result.json<br>        echo "result=$(cat diff_result.json)" >> $GITHUB_OUTPUT<br>    - name: Comment on PR<br>      if: steps.diff.outputs.result != '{}'<br>      uses: actions/github-script@v7<br>      with:<br>        script: |<br>          const result = JSON.parse('${{ steps.diff.outputs.result }}');<br>          if (result.breaking_changes.length > 0) {<br>            github.rest.issues.createComment({<br>              issue_number: context.issue.number,<br>              owner: context.repo.owner,<br>              repo: context.repo.repo,<br>              body: `❌ **Contract Diff Gate Failed**\\n\\n**Breaking Changes Detected:**\\n${result.breaking_changes.map(c => `- ${c}`).join('\\n')}\\n\\n**Action Required:** Submit Architecture Conflict Report to ARB.`<br>            });<br>          }<br>``` | PR 提交修改 Universal Contract Schema 时，Job 运行，检测到 breaking changes → PR 自动评论 ❌，合并被阻断 |
| **测试验证** | Platform Team | 1. 创建测试 PR：故意修改 `Asset.json` 添加字段 → 确认 Job 失败、评论生成<br>2. 创建测试 PR：修改 Industry Package 下的文件 → 确认 Job 通过 | 两种场景均表现正确 |

### 🔴 P0-04: Smart Park v1.0 Asset Package 打包 (Day 3-5)

#### 4.1 Manifest 定稿
| 文件 | 路径 | 必填字段 | 负责人 |
|------|------|----------|--------|
| `asset-package.yaml` | `packages/industry/smart-park/asset-package.yaml` | ```yaml<br>name: "smart-park"<br>version: "1.0.0"<br>description: "DT-Lite V4.0 Smart Park Industry Asset Package"<br>universal_contract_version: "1.0.0"<br>dependencies:<br>  - name: "dt-lite-core"<br>    version: ">=4.0.0"<br>schemas:<br>  - "schemas/universal/*.json"<br>templates:<br>  - "templates/*.yaml"<br>profiles:<br>  - "profiles/*.yaml"<br>scenarios:<br>  - "scenarios/*.yaml"<br>``` | Architecture Lead |

#### 4.2 AssetTemplates 打包 (20+ 个)
| 目录 | 路径 | 要求 | 负责人 |
|------|------|------|--------|
| Building 类 | `packages/industry/smart-park/templates/building/` | Building.yaml, Floor.yaml, Zone.yaml, Room.yaml | Industry Team |
| HVAC 类 | `packages/industry/smart-park/templates/hvac/` | AHU.yaml, FCU.yaml, Chiller.yaml, Pump.yaml, CoolingTower.yaml, VAV.yaml | Industry Team |
| Energy 类 | `packages/industry/smart-park/templates/energy/` | Transformer.yaml, Switchgear.yaml, Meter.yaml, PDU.yaml, UPS.yaml, SolarInverter.yaml | Industry Team |
| Water 类 | `packages/industry/smart-park/templates/water/` | WaterMeter.yaml, Pump.yaml, Valve.yaml, Tank.yaml, WaterQualitySensor.yaml | Industry Team |
| Security 类 | `packages/industry/smart-park/templates/security/` | Camera.yaml, AccessController.yaml, AlarmPanel.yaml, IntrusionDetector.yaml | Industry Team |
| Transport 类 | `packages/industry/smart-park/templates/transport/` | Elevator.yaml, Escalator.yaml, ParkingGate.yaml, EVCharger.yaml, AGV.yaml | Industry Team |
| Environment 类 | `packages/industry/smart-park/templates/environment/` | AirQualitySensor.yaml, TemperatureSensor.yaml, HumiditySensor.yaml, NoiseSensor.yaml, LightSensor.yaml | Industry Team |
| Production 类 | `packages/industry/smart-park/templates/production/` | ProductionLine.yaml, Machine.yaml, Robot.yaml, CNC.yaml, AGV.yaml | Industry Team |
| Fire 类 | `packages/industry/smart-park/templates/fire/` | FireDetector.yaml, Sprinkler.yaml, FireHydrant.yaml, FirePump.yaml, SmokeExhaustFan.yaml | Industry Team |
| IT 类 | `packages/industry/smart-park/templates/it/` | Server.yaml, Switch.yaml, Router.yaml, Firewall.yaml, Storage.yaml | Industry Team |

**每个 Template 必须包含**：
```yaml
# 示例: Building.yaml
apiVersion: dt-lite.io/v1
kind: AssetTemplate
metadata:
  name: building
  version: "1.0.0"
  category: building
  code: "asset.park.building.building"
spec:
  assetSchema:
    type: object
    properties:
      name: {type: string}
      address: {type: string}
      floors: {type: integer, minimum: 1}
      grossArea: {type: number, unit: "m2"}
      constructionYear: {type: integer}
    required: [name, address, floors]
  pointTemplates:
    - code: "asset.park.building.power_active"
      semanticType: "power"
      unit: "kW"
      aggregation: "sum"
    - code: "asset.park.building.energy_total"
      semanticType: "energy"
      unit: "kWh"
      aggregation: "sum"
  capabilityTemplates:
    - code: "capability.building.energy_report"
      category: "report"
      safetyLevel: "C0"
  instantiationParamsSchema:
    type: object
    properties:
      name: {type: string}
      address: {type: string}
      floors: {type: integer}
    required: [name, address, floors]
```

#### 4.3 CompositeTemplates 打包 (10+ 个)
| 文件 | 路径 | 组合逻辑 | 负责人 |
|------|------|----------|--------|
| BuildingComplex.yaml | `packages/industry/smart-park/templates/composite/` | Building + Floors + Zones + Rooms (Tree) | Industry Team |
| HVACSystem.yaml | `packages/industry/smart-park/templates/composite/` | Chiller + Pumps + AHUs + FCUs + CoolingTower (Tree+Graph) | Industry Team |
| EnergyNetwork.yaml | `packages/industry/smart-park/templates/composite/` | Transformer + Switchgear + Meters + PDU + UPS (Graph) | Industry Team |
| WaterSystem.yaml | `packages/industry/smart-park/templates/composite/` | WaterMeter + Pumps + Valves + Tanks + QualitySensors | Industry Team |
| SecurityZone.yaml | `packages/industry/smart-park/templates/composite/` | Cameras + AccessControllers + AlarmPanels + Detectors | Industry Team |
| TransportHub.yaml | `packages/industry/smart-park/templates/composite/` | Elevators + Escalators + ParkingGates + EVChargers | Industry Team |
| ProductionCell.yaml | `packages/industry/smart-park/templates/composite/` | ProductionLine + Machines + Robots + CNCs + AGVs | Industry Team |
| FireProtection.yaml | `packages/industry/smart-park/templates/composite/` | Detectors + Sprinklers + Hydrants + Pumps + SmokeExhaust | Industry Team |
| ITInfrastructure.yaml | `packages/industry/smart-park/templates/composite/` | Servers + Switches + Routers + Firewalls + Storage | Industry Team |
| ParkCampus.yaml | `packages/industry/smart-park/templates/composite/` | 多 BuildingComplex + EnergyNetwork + TransportHub (Graph) | Industry Team |

#### 4.4 IntegrationProfiles & MappingProfiles 打包 (30+ Profiles, 200+ Mappings)
| 目录 | 路径 | 内容 | 负责人 |
|------|------|------|--------|
| BACnet | `packages/industry/smart-park/profiles/bacnet/` | BMS IntegrationProfile + 50+ MappingProfiles (HVAC, Lighting, Access, Fire, Elevator) | Industry Team |
| Modbus | `packages/industry/smart-park/profiles/modbus/` | Energy Meters, Water Meters, Environmental Sensors MappingProfiles | Industry Team |
| OPC UA | `packages/industry/smart-park/profiles/opcua/` | Production Equipment, PLCs MappingProfiles | Industry Team |
| MQTT | `packages/industry/smart-park/profiles/mqtt/` | IoT Gateways, Environmental Sensors, EV Chargers MappingProfiles | Industry Team |
| REST | `packages/industry/smart-park/profiles/rest/` | ERP, CMMS, Weather Service MappingProfiles | Industry Team |
| OCPP | `packages/industry/smart-park/profiles/ocpp/` | EV Charging Stations MappingProfiles | Industry Team |

**MappingProfile 示例**：
```yaml
# profiles/bacnet/hvac/ahu-supply-temp.yaml
apiVersion: dt-lite.io/v1
kind: MappingProfile
metadata:
  name: ahu-supply-temp-bacnet
  version: "1.0.0"
spec:
  protocol: "bacnet"
  pointCode: "asset.park.hvac.ahu.supply_temp"
  mapping:
    deviceId: "bacnet:device:{{ .device_instance }}"
    objectType: "analog-input"
    objectInstance: "{{ .supply_temp_instance }}"
    property: "present-value"
  transform:
    type: "linear"
    scale: 0.1
    offset: -40
  polling:
    interval: 30
    timeout: 5
    deadband: 0.5
```

#### 4.5 ScenarioTemplates 打包 (GS-01~10)
| 文件 | 路径 | 对应场景 | 负责人 |
|------|------|----------|--------|
| energy-management.yaml | `packages/industry/smart-park/scenarios/` | GS-01 | Industry Team |
| hvac-optimization.yaml | `packages/industry/smart-park/scenarios/` | GS-02 | Industry Team |
| water-management.yaml | `packages/industry/smart-park/scenarios/` | GS-03 | Industry Team |
| security-access.yaml | `packages/industry/smart-park/scenarios/` | GS-04 | Industry Team |
| transport-parking.yaml | `packages/industry/smart-park/scenarios/` | GS-05 | Industry Team |
| environment-monitoring.yaml | `packages/industry/smart-park/scenarios/` | GS-06 | Industry Team |
| production-monitoring.yaml | `packages/industry/smart-park/scenarios/` | GS-07 | Industry Team |
| fire-safety.yaml | `packages/industry/smart-park/scenarios/` | GS-08 | Industry Team |
| integrated-operations.yaml | `packages/industry/smart-park/scenarios/` | GS-09 | Industry Team |
| zero-code-assembly.yaml | `packages/industry/smart-park/scenarios/` | GS-10 | Industry Team |

#### 4.6 Helm Values 与发布脚本
| 文件 | 路径 | 要求 | 负责人 |
|------|------|------|--------|
| `values-smart-park.yaml` | `deployment/helm/values-smart-park.yaml` | 完整参数化：replicaCounts, resources, ingress, persistence, externalSystems, featureFlags，**无硬编码** | DevOps Team |
| `release-smart-park-v1.0.sh` | `scripts/release-smart-park-v1.0.sh` | 一键：校验 Manifest → 打包 Helm Chart → 渲染 values → 运行 contract-diff → 推送 Chart Museum → 生成 Release Notes | DevOps Team |

---

## 📋 Phase 1: Smart Park v1.0 生产就绪 (Week 2-3, Sep 23 - Oct 6)

### 🟡 P1-01: 部署验证矩阵执行

#### 环境准备清单
| 环境 | Kubernetes 集群 | 命名空间 | 数据库 | 消息队列 | 存储 | 负责人 |
|------|----------------|----------|--------|----------|------|--------|
| **Dev** | dev-k8s | dt-lite-dev | PostgreSQL (dev) | EMQX (dev) | MinIO (dev) | DevOps |
| **Staging** | staging-k8s | dt-lite-staging | PostgreSQL (staging) | EMQX (staging) | MinIO (staging) | DevOps |
| **Pre-Prod** | preprod-k8s | dt-lite-preprod | PostgreSQL (preprod) | EMQX (preprod) | MinIO (preprod) | DevOps |
| **Prod Canary** | prod-k8s | dt-lite-prod-canary | PostgreSQL (prod) | EMQX (prod) | MinIO (prod) | DevOps |

#### 部署验证脚本 (每个环境必跑)
```bash
#!/bin/bash
# scripts/verify-deployment.sh <environment>
ENV=$1
NAMESPACE="dt-lite-${ENV}"

echo "=== Deploying Smart Park v1.0 to ${ENV} ==="
helm upgrade --install smart-park deployment/helm/smart-park \
  -n ${NAMESPACE} \
  -f deployment/helm/values-smart-park.yaml \
  -f deployment/helm/values-${ENV}.yaml \
  --wait --timeout 10m

echo "=== Running GS-01~10 Integration Tests ==="
kubectl run gs-test-${ENV} --rm -i --restart=Never \
  --image=dt-lite/gs-runner:latest \
  -n ${NAMESPACE} \
  -- python -m pytest tests/golden/ -v --junitxml=/tmp/gs-results.xml

echo "=== Performance Test (5min load) ==="
kubectl run perf-test-${ENV} --rm -i --restart=Never \
  --image=dt-lite/perf-test:latest \
  -n ${NAMESPACE} \
  -- python scripts/cp3_load_test.py --duration 300 --endpoint http://api-gateway:8000

echo "=== Checking Results ==="
# 解析 junitxml 和性能报告，输出 PASS/FAIL
```

#### 验收门禁检查表 (每环境)
| 检查项 | 命令/方法 | 通过标准 | 记录位置 |
|--------|-----------|----------|----------|
| **Pod 就绪** | `kubectl get pods -n $NS -l app.kubernetes.io/instance=smart-park` | 所有 Pod Running/Ready, 0 Restarts | 部署日志 |
| **API 健康** | `curl -f http://gateway.$ENV.dt-lite.io/health` | 200 OK, 响应 < 100ms | 监控面板 |
| **GS-01~10** | `pytest tests/golden/ --junitxml=results.xml` | 337 tests pass, 0 failed | CI Artifacts |
| **P95 延迟** | Grafana Query: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | < 200ms | Grafana Dashboard |
| **错误率** | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | < 0.1% | Grafana Dashboard |
| **数据完整性** | 对比 Pre-Prod 真实 BMS 数据 vs 平台入库数据 | 100% 匹配, 0 丢失 | 数据质量报告 |
| **告警准确率** | 注入已知故障 → 检查告警触发 | > 95% 准确, 0 漏报/误报 | 告警验收记录 |
| **安全扫描** | `trivy image --severity CRITICAL,HIGH dt-lite/*:v1.0.0` | 0 Critical, 0 High | Trivy Report |

### 🟡 P1-02: 运维手册套件编写 (并行进行)

| 手册 | 路径 | 核心章节 | 负责人 | 截止 |
|------|------|----------|--------|------|
| **运行手册** | `docs/operations/smart-park-runbook.md` | 1. 架构概览 2. 部署步骤 3. 扩缩容 4. 备份恢复 5. 故障排查决策树 6. 常用运维命令 7. 版本升级/回滚 | DevOps Lead | Week 2 Day 3 |
| **容量规划** | `docs/operations/smart-park-capacity.md` | 1. 资源模型 (CPU/Memory/Storage/Network per service) 2. 扩容触发阈值 3. 成本估算 (不同规模园区) 4. 压测基准数据 | DevOps Lead | Week 2 Day 3 |
| **告警手册** | `docs/operations/smart-park-alerts.md` | 1. 全量告警清单 (名称、级别、含义、影响) 2. 分级响应 SOP (P0/P1/P2/P3) 3. 通知渠道配置 4. 逃逸机制 | DevOps Lead | Week 2 Day 4 |
| **升级指南** | `docs/operations/smart-park-upgrade.md` | 1. 升级策略 (蓝绿/滚动/金丝雀) 2. 版本兼容性矩阵 3. 数据迁移脚本 4. 回滚决策树 5. 灰度发布步骤 | DevOps Lead | Week 2 Day 5 |
| **安全加固** | `docs/operations/smart-park-hardening.md` | 1. 网络策略 2. RBAC 矩阵 3. 审计日志配置 4. 加密 (传输/静态) 5. 漏洞扫描与修复流程 | Security Lead | Week 3 Day 2 |

**编写规范**：
- 每个操作步骤必须有 `命令` + `预期输出` + `异常处理`
- 所有脚本放入 `scripts/operations/` 目录，手册引用脚本路径
- 手册版本与 Smart Park v1.0 绑定，放入 Helm Chart `templates/_runbooks.tpl`

### 🟡 P1-03: Go/No-Go 生产发布决策会 (Week 3 Day 5)

| 参会角色 | 决策输入 | 决策输出 |
|----------|----------|----------|
| Architecture Lead | 架构合规性确认 | ✅/❌ |
| QA Lead | 测试报告 (功能/性能/安全/稳定性) | ✅/❌ |
| DevOps Lead | 部署验证矩阵结果、运维手册完整性 | ✅/❌ |
| Security Lead | 安全扫描报告、加固清单完成度 | ✅/❌ |
| Industry Lead (Park) | 业务场景验收 (GS-01~10、真实数据对比) | ✅/❌ |
| PO | 业务价值确认、用户验收 | ✅/❌ |
| **dt_manager** | **最终裁决** | **GO / NO-GO** |

**GO 标准**：所有角色 ✅，无 P0/P1 阻塞问题，**全票通过**  
**NO-GO**：任一角色 ❌，必须给出具体阻塞项、整改计划、复测时间

---

## 🛠️ 开发规范强制要求 (全阶段通用)

### 代码提交规范
```bash
# 每次提交必须包含：
# 1. 关联 Issue: fixes #ISSUE_NUMBER
# 2. 变更类型: feat/fix/docs/refactor/test/chore
# 3. Contract 影响声明: [Contract: NONE/MODIFIED] (修改必须走 ARB)

# 示例:
git commit -m "feat(asset): add building composite template

- Add BuildingComplex CompositeAsset template
- Include floors, zones, rooms hierarchy
- Add capability inheritance for energy reporting

fixes #1234
[Contract: NONE]"
```

### 分支策略
| 分支类型 | 命名规范 | 用途 | 合并目标 |
|----------|----------|------|----------|
| **Feature** | `feat/<issue-id>-<short-desc>` | 新功能开发 | `main` (via PR) |
| **Bugfix** | `fix/<issue-id>-<short-desc>` | 缺陷修复 | `main` / `release/*` |
| **Hotfix** | `hotfix/<version>-<desc>` | 生产紧急修复 | `main` + `release/*` |
| **Release** | `release/uaa-v1.0-frozen` | 基线冻结 | **只读**, 仅接受 hotfix |

### Code Review Checklist (每个 PR 必填)
```markdown
## Code Review Checklist

### Architecture Compliance
- [ ] 未修改 Universal Contract v1.0 (schemas/universal/*.json)
- [ ] Industry Package 仅消费 Core SDK，无直接 DB 操作
- [ ] 新业务功能通过 Assembly Engine/Studio Tools 实现 (非硬编码)
- [ ] 符合 Naming Convention: `asset.park.<sub>.<type>`

### Code Quality
- [ ] 单测覆盖率 ≥ 80% (新增代码)
- [ ] 集成测覆盖率 ≥ 70% (API 契约)
- [ ] 无 lint 错误 (ruff/mypy/eslint)
- [ ] 类型提示完整 (Python: strict, TypeScript: strict)

### Testing
- [ ] 单测通过: `pytest tests/<module>/ -v`
- [ ] 集成测通过: `pytest tests/integration/ -v`
- [ ] 架构测通过: `pytest tests/architecture/ -v`
- [ ] Contract Diff: `make contract-diff` (本地预检)

### Documentation
- [ ] API 变更更新 OpenAPI Spec
- [ ] 新功能更新 Runbook/用户手册
- [ ] 破坏性变更包含迁移指南
- [ ] CHANGELOG.md 更新
```

---

## 📅 每日站会 & 周报模板

### 每日站会 (15min, 10:00)
```
1. 昨日完成: [具体任务, 对应 Issue #]
2. 今日计划: [具体任务, 对应 Issue #]
3. 阻塞项: [具体描述, 需要谁协助, 预计解决时间]
4. Contract 合规: [是否涉及 Contract 变更, 是否已跑 contract-diff]
```

### 周报 (周五 17:00 前提交)
```
## Week N Progress (Team: <Team Name>)

### Completed
- [Issue #] <Description> - <Link to PR/Artifact>

### In Progress
- [Issue #] <Description> - <Status: % complete> - <Blockers>

### Metrics
- Tests: <passed>/<total> (<pass_rate>%)
- Coverage: Unit <x>%, Integration <y>%
- Contract Diff Runs: <count>, Failures: <count>
- Deployments: <env> - <status>

### Risks
- <Risk Description> - <Mitigation> - <Owner>

### Next Week Focus
- <Priority 1>
- <Priority 2>
- <Priority 3>
```

---

## 📞 升级路径与联系人

| 问题类型 | 首选联系人 | 升级路径 | 响应 SLA |
|----------|------------|----------|----------|
| **Contract 合规/冲突** | Architecture Lead | → dt_manager → CTO | 2h |
| **CI/CD Pipeline 失败** | Platform Lead | → DevOps Lead → Architecture Lead | 1h |
| **部署/环境问题** | DevOps Lead | → Platform Lead → Architecture Lead | 30min (Prod) / 2h (其他) |
| **业务需求变更/澄清** | Industry Lead | → PO → dt_manager | 4h |
| **安全/合规问题** | Security Lead | → Platform Lead → CTO | 即时 |
| **跨团队依赖/冲突** | dt_manager | → CTO | 4h |

---

## ✅ 立即行动清单 (收到此文档后 2 小时内)

| # | 动作 | 负责人 | 完成标志 |
|---|------|--------|----------|
| 1 | 确认理解本文档所有内容，在钉钉/飞书群回复“已阅” | 全员 | 群内全员✅ |
| 2 | 本地拉取最新 main，跑全量测试 `pytest -x` 确认 337 passed | 全员开发 | 终端截图发群 |
| 3 | 本地跑 `make contract-diff` 确认无 breaking changes | 全员开发 | 终端截图发群 |
| 4 | Platform Team: 开始 P0-01 Git 标记/分支保护 | Platform Lead | Tag + 分支保护生效 |
| 5 | Architecture Team: 开始 P0-02 文档归档/制品注册 | Architecture Lead | 11 Artifacts 注册成功 |
| 6 | Platform Team: 开始 P0-03 contract-diff CI Job 开发 | Platform Team | PR #xxxx 提交 |
| 7 | Industry Team: 开始 P0-04 Smart Park 打包任务认领 | Industry Lead | 任务分配表发群 |
| 8 | DevOps Team: 准备 4 套环境集群、数据库、MQ、存储 | DevOps Lead | 环境清单确认表发群 |

---

## 📝 附录：关键路径文件速查

| 类型 | 路径 | 说明 |
|------|------|------|
| **Universal Contract Schemas** | `packages/schemas/universal/*.json` | **冻结，只读** |
| **Baseline Schemas** | `packages/schemas/universal/baseline/*.json` | CI Diff 基线 |
| **Core Services** | `services/core/src/` | 核心域服务 |
| **IoT Services** | `services/iot/src/` | 协议适配、发现、映射 |
| **Twin Services** | `services/twin/src/` | 场景、绑定、3D |
| **Application Services** | `services/application/src/` | Dashboard、LargeScreen、Assembly、Workflow |
| **Telemetry Services** | `services/telemetry/src/` | KPI、Alarm |
| **AI Services** | `services/ai/src/` | Tool、Agent、Safety、Audit |
| **Smart Park Package** | `packages/industry/smart-park/` | **Phase 0 重点交付** |
| **Smart Factory Package** | `packages/industry/smart-factory/` | Phase 2 交付 |
| **Helm Charts** | `deployment/helm/` | 部署包 |
| **Tests** | `tests/` | 单测/集成/架构/黄金/兼容性 |
| **Scripts** | `scripts/` | 部署、验证、负载、发布脚本 |
| **Docs** | `docs/` | 架构、运维、开发者文档 |

---

**文档状态**：✅ 生效执行
**下次同步**：Daily Standup 10:00
**文档位置**：`docs/architecture/asset-packages/smart-park/DT-Lite_V4.0_Dev_Team_Work_Instructions_Phase0_Phase1.md`

---

> **最后强调**：
> - **Universal Contract v1.0 已冻结**，任何修改尝试 = 违规
> - **Contract Diff Gate 已接入 CI**，PR 必跑，失败即阻断
> - **Phase 0 任务今天必须全部启动**，周五前全部完成
> - **有问题立即升级**，不等、不拖、不隐瞒

**全员执行，零容忍，交付 Smart Park v1.0 生产就绪！** 🚀