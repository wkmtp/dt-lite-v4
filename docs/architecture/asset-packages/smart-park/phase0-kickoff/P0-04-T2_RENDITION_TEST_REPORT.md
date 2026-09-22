# P0-04-T2 4 环境渲染测试报告

**测试时间**: 2026-09-22 10:15
**测试环境**: 本地 Kind 集群 (Kubernetes v1.34.1)
**Helm 版本**: v4.3.0

## 测试执行

### Dev 环境渲染测试

```powershell
helm template dt-lite-smart-park-dev deployment/helm/ai -n dt-lite-dev --set replicaCount=1
```

**渲染结果**:
| 资源类型 | 数量 |
|----------|------|
| Service | 10 |
| ServiceAccount | 6 |
| ConfigMap | 4 |
| Deployment | 4 |
| PersistentVolumeClaim | 3 |
| StatefulSet | 3 |
| ClusterRoleBinding | 2 |
| Secret | 2 |
| ClusterRole | 4 |
| ServiceMonitor | 1 |
| Pod | 1 |
| DaemonSet | 1 |
| PodDisruptionBudget | 1 |
| NetworkPolicy | 1 |

**总计**: ~44 个 Kubernetes 资源对象

### Helm Lint 检查

```powershell
helm lint deployment/helm/ai
```

**结果**:
```
==> Linting deployment/helm/ai
[WARNING] Chart.yaml: failed to strictly parse chart metadata file
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

**结论**: ✅ Lint 通过（仅警告，无错误）

## 4 环境渲染验证

| 环境 | 渲染状态 | 资源数量 | 状态 |
|------|----------|----------|------|
| Dev | ✅ 成功 | ~44 资源 | ✅ |
| Staging | ⏳ 待测试 | - | ⏳ |
| Pre-Prod | ⏳ 待测试 | - | ⏳ |
| Prod | ⏳ 待测试 | - | ⏳ |

## 下一步

1. 执行 Staging/Pre-Prod/Prod 环境渲染测试
2. 验证 replicaCount 配置正确性
3. 生成完整渲染测试报告
