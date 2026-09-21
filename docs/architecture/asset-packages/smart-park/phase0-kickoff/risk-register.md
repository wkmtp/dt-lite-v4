# Phase 0 风险登记册

**创建时间**：2026-09-16 16:11  
**版本**：v1.0  
**维护人**：dt_manager

## 风险清单

| ID | 风险描述 | 影响 | 可能性 | 对策 | 责任人 | 截止 | 状态 |
|----|----------|------|--------|------|--------|------|------|
| R-01 | 分支保护规则未及时生效导致误推 | 高 | 中 | 今晚 20:00 前强制完成，设置 GitHub Alert 告警 | Platform Lead | 20:00 | 🔴 |
| R-02 | Artifacts 注册失败/路径错误 | 中 | 低 | 预先校验 11 路径存在，分批注册，确认 File link | Architecture Team | 20:00 | 🟢 |
| R-03 | 4 环境 Helm values 渲染差异 | 高 | 中 | 今日跑 4 遍渲染对比，锁定 values 版本，输出渲染日志 | DevOps Team | 22:00 | 🟡 |
| R-04 | P0-03 contract-diff 工具开发延期 | 高 | 中 | 明日会上拆解为 3 个并行子任务，Day 2 中期检查 | Platform Lead | Day 3 | 🟡 |
| R-05 | Smart Park 打包制品不全/版本漂移 | 高 | 中 | Industry Lead 今晚清单对齐 Freeze Report §Baseline，Day 3 中期检查 | Industry Lead | Day 5 | 🟡 |
| R-06 | 全员学习曲线陡峭导致 UAA 合规率下降 | 高 | 高 | 强制培训考核 + 脚手架强约束 + Code Review 必过 Contract Check | dt_manager | Week 2 | 🟡 |
| R-07 | 版本管理混乱 (SemVer 违规) | 中 | 中 | 统一 SemVer 规范，依赖锁文件，定期依赖扫描 | Platform Lead | Week 3 | 🟡 |
| R-08 | CI/CD pipeline 不稳定导致阻塞 | 中 | 中 | contract-diff CI Job 优先保障，其余 Job 降级为 warning | Platform Lead | Day 3 | 🟡 |
| R-09 | Smart Factory 兼容性误报/漏报 | 中 | 低 | 完善 diff 算法 + 白名单机制 + 定期回归测试 | Platform Lead | Week 4 | 🟢 |
| R-10 | 安全扫描发现 Critical/High 漏洞 | 高 | 低 | Phase 1 同步执行安全扫描，0 Critical/High 才准入 Prod | Security Lead | Week 3 | 🟢 |
| R-11 | 本地 Kind 测试通过但远程集群未就绪 | 中 | 高 | 使用本地测试作为预验证，远程集群部署时重新测试 | DevOps Team | Week 2 | 🟡 |
| R-12 | GitHub Actions Workflow 配置错误 | 中 | 中 | 本地测试闭环后部署，Workflow 使用 Secrets 保护集群凭证 | Platform Lead | Week 2 | 🟡 |

## 风险趋势图

```
🔴 高 | R-01    R-03 R-04 R-05         R-10
🟡 中 |         R-02    R-06 R-07 R-08 R-09 R-11 R-12
🟢 低 |
     └─────────────────────────────────────
       D0  D1  D2  D3  D4  D5  W2  W3  W4
```

## 升级路径

| 风险级别 | 响应时间 | 升级路径 |
|----------|----------|----------|
| 🔴 紧急 | 1h | → dt_manager → CTO |
| 🟡 警告 | 4h | → 领域 Lead → dt_manager |
| 🟢 观察 | 24h | → 领域 Lead 跟踪 |

## 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| 2026-09-16 | 初始版本，10 条风险 | dt_manager |
| 2026-09-21 | 新增 R-11 (本地测试通过但远程集群未就绪)、R-12 (GitHub Actions Workflow 配置错误) | dt_manager |
