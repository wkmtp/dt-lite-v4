# Phase 1 远程 K8s 集群部署及迁移指南

**文档版本**: v1.0
**创建时间**: 2026-09-22 09:55
**负责人**: dt_manager (Platform Lead)
**适用环境**: Staging / Pre-Prod / Prod

---

## 📋 目录

1. [架构概览](#1-架构概览)
2. [前置条件](#2-前置条件)
3. [环境准备](#3-环境准备)
4. [部署步骤](#4-部署步骤)
5. [验证测试](#5-验证测试)
6. [迁移检查清单](#6-迁移检查清单)
7. [故障排查](#7-故障排查)
8. [回滚方案](#8-回滚方案)

---

## 1. 架构概览

### **1.1 目标架构**

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Control    │  │   Node 1    │  │   Node 2    │  ...    │
│  │   Plane     │  │  (AZ-a)     │  │  (AZ-b)     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────▼────────────────▼────────────────▼──────────┐     │
│  │              Namespace: dt-lite-prod               │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │     │
│  │  │  AI Service │  │ PostgreSQL  │  │   Redis     │ │     │
│  │  │  (5 pods)   │  │   (HA)      │  │   (HA)      │ │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │     │
│  │  │  Prometheus │  │   Grafana   │  │  Ingress    │ │     │
│  │  │   (Scrape)  │  │  (Monitor)  │  │  (WAF)      │ │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### **1.2 环境对比**

| 环境 | 节点数 | AZ 分布 | 副本数 | 用途 |
|------|--------|---------|--------|------|
| **Dev** | 3 | 单 AZ | 1 | 开发测试 |
| **Staging** | 3 | 单 AZ | 2 | 集成测试 |
| **Pre-Prod** | 5 | 多 AZ | 3 | 性能压测 |
| **Prod** | 7+ | 多 AZ | 5 | 生产运行 |

---

## 2. 前置条件

### **2.1 基础设施**

| 组件 | 要求 | 验证命令 |
|------|------|----------|
| **Kubernetes** | v1.28+ | `kubectl version` |
| **Helm** | v3.13+ | `helm version` |
| **节点** | 4 CPU, 8GB RAM × N | `kubectl get nodes` |
| **StorageClass** | 至少 1 个默认 SC | `kubectl get sc` |
| **Ingress Controller** | nginx/apache | `kubectl get ingressclass` |

### **2.2 权限配置**

```bash
# 创建 ServiceAccount
kubectl create serviceaccount dt-lite-admin -n dt-lite-prod

# 绑定 ClusterRole
kubectl create clusterrolebinding dt-lite-admin-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=default:dt-lite-admin
```

### **2.3 镜像仓库**

```bash
# 推送镜像到远程仓库
docker build -t registry.example.com/dt-lite-ai:4.0.0 .
docker push registry.example.com/dt-lite-ai:4.0.0

# 或在 values.yaml 中配置 imagePullSecrets
# values-prod.yaml:
# imagePullSecrets:
#   - name: registry-secret
```

---

## 3. 环境准备

### **3.1 创建 Namespace 和配额**

```bash
#!/bin/bash
# setup-namespace.sh
ENV=$1
NAMESPACE="dt-lite-$ENV"

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    environment: $ENV
    team: dt-lite
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dt-lite-quota
  namespace: $NAMESPACE
spec:
  hard:
    requests.cpu: "16"
    requests.memory: 32Gi
    limits.cpu: "32"
    limits.memory: 64Gi
    pods: "100"
EOF
```

**执行**:
```bash
chmod +x setup-namespace.sh
./setup-namespace.sh prod
./setup-namespace.sh preprod
./setup-namespace.sh staging
```

### **3.2 配置 NetworkPolicy**

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dt-lite-default-deny
  namespace: dt-lite-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dt-lite-allow-internal
  namespace: dt-lite-prod
spec:
  podSelector:
    matchLabels:
      app: dt-lite-ai
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: dt-lite-prod
    - podSelector: {}
```

### **3.3 配置 Prometheus 监控**

```yaml
# monitoring.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: dt-lite-alerts
  namespace: dt-lite-prod
spec:
  groups:
  - name: dt-lite.rules
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate on {{ $labels.instance }}"
```

---

## 4. 部署步骤

### **4.1 准备 Values 文件**

```yaml
# values-prod.yaml
replicaCount: 5

image:
  repository: registry.example.com/dt-lite-ai
  tag: "4.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

affinity:
  podAntiAffinity: hard

postgresql:
  enabled: true
  auth:
    existingSecret: dt-lite-db-secret
    secretKeys:
      adminPasswordKey: postgres-password

redis:
  enabled: true
  auth:
    existingSecret: dt-lite-redis-secret

prometheus:
  enabled: true
  scrapeInterval: 15s
```

### **4.2 创建 Secret**

```bash
# 创建数据库密码 Secret
kubectl create secret generic dt-lite-db-secret \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  -n dt-lite-prod

# 创建 Redis 密码 Secret
kubectl create secret generic dt-lite-redis-secret \
  --from-literal=password=$(openssl rand -base64 32) \
  -n dt-lite-prod

# 创建应用配置 Secret
kubectl create secret generic dt-lite-app-secret \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  -n dt-lite-prod
```

### **4.3 执行部署**

```bash
#!/bin/bash
# deploy.sh
ENV=$1
NAMESPACE="dt-lite-$ENV"
RELEASE="dt-lite-smart-park-$ENV"
VALUES_FILE="values-$ENV.yaml"

echo "========================================"
echo "部署 $ENV 环境"
echo "========================================"

# 检查 prerequisites
helm dependency update deployment/helm/ai

# 部署
helm upgrade --install "$RELEASE" deployment/helm/ai \
  -n "$NAMESPACE" \
  -f "$VALUES_FILE" \
  --wait \
  --timeout 600s \
  --atomic

# 验证
helm test "$RELEASE" -n "$NAMESPACE" --logs --timeout 10m

echo "✅ $ENV 环境部署完成"
```

**执行**:
```bash
chmod +x deploy.sh
./deploy.sh prod
./deploy.sh preprod
./deploy.sh staging
```

---

## 5. 验证测试

### **5.1 基础验证**

```bash
# 检查 Pod 状态
kubectl get pods -n dt-lite-prod -l app=dt-lite-ai

# 检查 Service
kubectl get svc -n dt-lite-prod

# 检查 Helm Release
helm list -n dt-lite-prod

# 运行 Helm Test
helm test dt-lite-smart-park-prod -n dt-lite-prod --logs
```

### **5.2 健康检查**

```bash
# 检查 Pod 日志
kubectl logs -n dt-lite-prod -l app=dt-lite-ai --tail=100

# 检查容器内进程
kubectl exec -n dt-lite-prod -l app=dt-lite-ai -- ps aux

# 测试 API 端点
kubectl port-forward -n dt-lite-prod svc/dt-lite-smart-park-prod-ai 8080:80
curl http://localhost:8080/health
```

### **5.3 性能基准**

```bash
# 资源使用监控
kubectl top pods -n dt-lite-prod -l app=dt-lite-ai
kubectl top nodes

# 负载测试（使用 wrk）
wrk -t12 -c400 -d30s http://localhost:8080/health
```

---

## 6. 迁移检查清单

### **6.1 迁移前检查**

- [ ] 本地 Kind 集群测试通过（✅ 已完成）
- [ ] Helm chart lint 通过
- [ ] 4 环境渲染测试通过
- [ ] 镜像已推送到远程仓库
- [ ] Secret 已创建
- [ ] Namespace 和资源配额已配置
- [ ] NetworkPolicy 已配置
- [ ] Prometheus 监控已配置

### **6.2 迁移执行检查**

- [ ] Dev 环境部署成功
- [ ] Staging 环境部署成功
- [ ] Pre-Prod 环境部署成功
- [ ] Prod 环境灰度发布成功
- [ ] 所有环境 Helm Test 通过
- [ ] 监控大盘配置完成
- [ ] 告警规则配置完成

### **6.3 迁移后验证**

- [ ] API 响应时间 < 200ms (p95)
- [ ] 错误率 < 0.1%
- [ ] 资源使用 < 70%
- [ ] 告警通知正常
- [ ] 备份恢复演练成功
- [ ] 回滚脚本可用

---

## 7. 故障排查

### **7.1 Pod 无法启动**

```bash
# 查看 Pod 状态
kubectl describe pod -n dt-lite-prod -l app=dt-lite-ai

# 常见问题：
# 1. ImagePullBackOff: 检查镜像仓库和 imagePullSecrets
# 2. CreateContainerConfigError: 检查 Secret 是否存在
# 3. CrashLoopBackOff: 检查应用日志和配置
```

### **7.2 服务无法访问**

```bash
# 检查 Service
kubectl get svc -n dt-lite-prod

# 检查 Endpoint
kubectl get endpoints -n dt-lite-prod

# 检查 NetworkPolicy
kubectl get networkpolicy -n dt-lite-prod
```

### **7.3 资源不足**

```bash
# 检查节点资源
kubectl top nodes

# 检查配额
kubectl describe resourcequota -n dt-lite-prod

# 扩容节点或调整配额
```

---

## 8. 回滚方案

### **8.1 Helm 回滚**

```bash
# 查看历史版本
helm history dt-lite-smart-park-prod -n dt-lite-prod

# 回滚到上一个版本
helm rollback dt-lite-smart-park-prod <revision> -n dt-lite-prod

# 强制回滚（如果失败）
helm rollback --force dt-lite-smart-park-prod <revision> -n dt-lite-prod
```

### **8.2 手动回滚**

```bash
# 回滚镜像版本
helm upgrade dt-lite-smart-park-prod deployment/helm/ai \
  -n dt-lite-prod \
  --set image.tag=4.0.0-previous \
  --wait --timeout 300s

# 验证回滚
kubectl rollout status deployment/dt-lite-smart-park-prod-ai -n dt-lite-prod
```

### **8.3 紧急停止**

```bash
# 删除整个 Release
helm uninstall dt-lite-smart-park-prod -n dt-lite-prod

# 删除 Namespace（谨慎使用）
kubectl delete namespace dt-lite-prod
```

---

## 📎 附录

### **A. 环境变量参考**

```bash
# 开发环境
export DB_HOST=postgresql.dt-lite-dev.svc.cluster.local
export REDIS_HOST=redis.dt-lite-dev.svc.cluster.local
export AI_API_KEY=your-api-key

# 生产环境
export DB_HOST=postgresql.dt-lite-prod.svc.cluster.local
export REDIS_HOST=redis.dt-lite-prod.svc.cluster.local
```

### **B. 常用 kubectl 命令**

```bash
# 查看 Pod 日志
kubectl logs -n dt-lite-prod -l app=dt-lite-ai -f

# 进入 Pod 调试
kubectl exec -n dt-lite-prod -it -l app=dt-lite-ai -- /bin/sh

# 端口转发
kubectl port-forward -n dt-lite-prod svc/dt-lite-smart-park-prod-ai 8080:80
```

### **C. 监控大盘 URL**

| 环境 | Grafana URL |
|------|-------------|
| Dev | https://grafana-dev.dt-lite.io/d/dt-lite |
| Staging | https://grafana-staging.dt-lite.io/d/dt-lite |
| Pre-Prod | https://grafana-preprod.dt-lite.io/d/dt-lite |
| Prod | https://grafana.dt-lite.io/d/dt-lite |

---

**文档版本**: v1.0
**创建时间**: 2026-09-22 09:55
**负责人**: dt_manager (Platform Lead)
**状态**: ✅ 就绪
