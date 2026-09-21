# Phase 0 启动会材料包

**会议时间**: 2026-09-22 09:00-09:30
**会议形式**: 视频会议
**主持人**: dt_manager
**参会人员**: 全员

---

## 📋 会议议程

| 时间 | 内容 | 主持 | 输入 | 产出 |
|------|------|------|------|------|
| 09:00-09:15 | **基线确认**：6 项全绿过屏 | dt_manager | 本地评审意见 + 人工操作截图 | 基线正式生效声明 |
| 09:15-09:45 | **P0-03 任务书评审**：contract-diff CI Job | Platform Lead | `p003-contract-diff-ci.md` | 子任务分派表 + Day2 中期检查点 |
| 09:45-10:15 | **P0-04 任务书评审**：Smart Park v1.0 打包 | Industry Lead | `p004-smart-park-packaging.md` | 制品清单确认单 + Day5 交付清单 |
| 10:15-10:30 | **环境确认 + 风险登记册 + 快速培训** | 全员 | DevOps 4环境表 + risk-register | Phase 1 正式启动令 |

---

## ✅ 基线确认清单（6 项全绿）

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | Git Tag `v4.0.0-uaa-freeze` | ✅ | `git tag -l` 已推送 |
| 2 | 保护分支 `release/uaa-v1.0-frozen` | ✅ | `git branch -r` 已推送 |
| 3 | Freeze Report 只读标记 | ✅ | `git ls-files -v` → `h` flag |
| 4 | 11 Reports Agnes Artifacts | ✅ | 全部 Registered |
| 5 | 全量测试 553 passed | ✅ | `pytest -x -q` 通过 |
| 6 | Contract Diff = ZERO | ✅ | CI #9 通过 |

**新增确认项**:
| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 7 | 本地 Kind 测试 | ✅ | Pod Running + Helm Test Succeeded |
| 8 | GitHub Actions Workflow | ✅ | `helm-test-local-kind.yml` 已部署 |

---

## 📚 会议材料清单

### **必读文档（会前完成）**
1. [baseline-confirmation.md](baseline-confirmation.md) — 基线确认清单
2. [p003-contract-diff-ci.md](p003-contract-diff-ci.md) — P0-03 任务书
3. [p004-smart-park-packaging.md](p004-smart-park-packaging.md) — P0-04 任务书
4. [risk-register.md](risk-register.md) — 风险登记册
5. [LOCAL_KIND_TEST_REPORT.md](LOCAL_KIND_TEST_REPORT.md) — 本地测试报告

### **会议演示材料**
- PPT: `phase0-kickoff/presentation.pptx`（会前准备）
- 截图: GitHub Actions 运行截图、Kind 集群测试截图

---

## 🎯 Phase 1 执行计划（启动会后立即进入）

### **Week 2 (Sep 23-27) — Dev/Staging 部署验证**

| 任务 ID | 任务 | 交付物 | Go/No-Go 验收标准 | 负责 | 截止 |
|---------|------|--------|-------------------|------|------|
| **P1-T1** | Dev 环境全量部署 | Helm Release `dt-lite-smart-park-dev` | ✅ `helm test` 全绿<br>✅ API 响应 < 200ms (p95)<br>✅ 20 Golden Assets 全部实例化可用<br>✅ **GS-01~03 场景端到端跑通** | DevOps + Industry | Sep 27 |
| **P1-T2** | Staging 环境全量部署 | Helm Release `dt-lite-smart-park-staging` | ✅ 完整 Helm values 渲染无报错<br>✅ 外部系统模拟器 (BACnet/Modbus/OPC UA/MQTT) 就绪<br>✅ **GS-04~05 场景端到端跑通** | DevOps + Industry | Sep 27 |
| **P1-T3** | 5 份 Runbook 草稿 | `RUNBOOK_DEPLOY/OBSERVE/INTEGRATE/ASSET_LIFECYCLE/INCIDENT.md` | ✅ 覆盖部署/回滚/监控/接入/资产生命周期/故障处理<br>✅ 有可执行步骤、回滚触发条件、升级路径 | DevOps + SRE | Sep 27 |

### **Week 3 (Sep 30-Oct 6) — Pre-Prod/Prod 验证 + Go-Live**

| 任务 ID | 任务 | 交付物 | Go/No-Go 验收标准 | 负责 | 截止 |
|---------|------|--------|-------------------|------|------|
| **P1-T4** | Pre-Prod 压力测试 | 1000 assets 模拟负载报告 | ✅ CPU/内存/网络/存储 均 < 70%<br>✅ P99 延迟 < 500ms<br>✅ 0 Critical/High 安全漏洞 | DevOps + Security | Oct 3 |
| **P1-T5** | Prod 灰度发布 (10% 流量) | 灰度发布记录 + 监控大盘 | ✅ 错误率 < 0.1%<br>✅ 告警噪音 < 5%<br>✅ 回滚演练 < 5 min | DevOps + SRE | Oct 6 |
| **P1-T6** | 5 份 Runbook 定稿 | 正式版 Runbook 入库 | ✅ 经生产环境验证修正<br>✅ On-Call 排班表关联 | DevOps + SRE | Oct 6 |
| **P1-T7** | **Phase 1 总结报告** | `PHASE1_SUMMARY.md` | ✅ **GS-01~10 全部零代码端到端通过 (GS-10 验收)**<br>✅ 所有 Go/No-Go 绿灯 | Industry Lead | Oct 6 |

---

## ⚠️ 风险登记册（更新版）

| ID | 风险描述 | 影响 | 可能性 | 状态 | 对策 |
|----|----------|------|--------|------|------|
| R-01 | 分支保护规则未及时生效 | 高 | 中 | 🔴 | 今晚 20:00 前强制完成 |
| R-03 | 4 环境 Helm values 渲染差异 | 高 | 中 | 🟡 | 今日跑 4 遍渲染对比 |
| R-04 | P0-03 contract-diff 工具开发延期 | 高 | 中 | 🟡 | 明日会上拆解为 3 并行子任务 |
| R-05 | Smart Park 打包制品不全/版本漂移 | 高 | 中 | 🟡 | Industry Lead 今晚清单对齐 |
| R-06 | 全员学习曲线陡峭 | 高 | 高 | 🟡 | 强制培训考核 + 脚手架强约束 |
| **R-11** | **本地测试通过但远程集群未就绪** | **中** | **高** | **🟡** | **使用本地测试预验证，远程部署时重新测试** |
| **R-12** | **GitHub Actions Workflow 配置错误** | **中** | **中** | **🟡** | **本地测试闭环后部署，使用 Secrets 保护凭证** |

---

## 🎓 快速培训议程（10:15-10:30）

### **R-06 培训：UAA 合规快速入门**
| 时间 | 内容 | 讲师 |
|------|------|------|
| 10:15-10:20 | Universal Contract v1.0 核心概念 | dt_manager |
| 10:20-10:25 | Scope Lock 12 条禁止项解读 | Platform Lead |
| 10:25-10:30 | Code Review  checklist + Contract Diff 使用 | Industry Lead |

### **培训材料**
- 《UAA 合规快速入门指南》（会前准备）
- 《Scope Lock 检查清单》（会前准备）
- 《Contract Diff 使用教程》（会前准备）

---

## 📎 附录：本地测试命令记录

```bash
# === 环境检查 ===
kubectl cluster-info --context kind-dt-lite-lab
helm version
kubectl version --client

# === 部署准备 ===
cd D:\ai\itwin\dt-lite-v4
helm dependency update deployment/helm/ai
kubectl create namespace dt-lite-dev

# === 安装 ===
helm install dt-lite-smart-park-dev deployment/helm/ai \
  -n dt-lite-dev \
  --create-namespace \
  --set postgresql.enabled=false \
  --set redis.enabled=false \
  --set prometheus.enabled=false \
  --set replicaCount=1

# === 验证 ===
kubectl get pods -n dt-lite-dev
kubectl get pods -n dt-lite-dev -w
kubectl logs -n dt-lite-dev deploy/dt-lite-smart-park-dev-ai

# === Helm Test ===
helm test dt-lite-smart-park-dev -n dt-lite-dev --logs --timeout 10m

# === 清理（可选）===
# helm uninstall dt-lite-smart-park-dev -n dt-lite-dev
# kubectl delete namespace dt-lite-dev
```

---

**材料准备**: dt_manager
**材料时间**: 2026-09-21 19:45
**状态**: ✅ 就绪
