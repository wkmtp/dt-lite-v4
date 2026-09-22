# DT-Lite Smart Park v1.0 — Prod Deployment Script
# 负责人：DevOps Team
# 截止：2026-09-23 12:00

set -euo pipefail

ENV="prod"
NAMESPACE="dt-lite-prod"
RELEASE="dt-lite-smart-park-prod"
CHART_PATH="deployment/helm/ai"
VALUES_FILE="deployment/helm/ai/values-prod.yaml"

echo "========================================"
echo "DT-Lite Smart Park v1.0 — Prod 部署"
echo "========================================"
echo "环境：$ENV"
echo "Namespace：$NAMESPACE"
echo "Release：$RELEASE"
echo ""

# Step 1: 环境检查
echo "[Step 1] 环境检查..."
kubectl cluster-info
kubectl version --client
helm version
kubectl get nodes
kubectl get sc
echo ""

# Step 2: 创建 Namespace 和配额
echo "[Step 2] 创建 Namespace 和资源配额..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f $CHART_PATH/prod-resource-quota.yaml -n $NAMESPACE
echo "✅ Namespace 和配额创建完成"
echo ""

# Step 3: 创建 Secret
echo "[Step 3] 创建 Secret..."
kubectl create secret generic dt-lite-db-secret \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic dt-lite-redis-secret \
  --from-literal=password=$(openssl rand -base64 32) \
  -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
echo "✅ Secret 创建完成"
echo ""

# Step 4: 准备 Values 文件
echo "[Step 4] 准备 Values 文件..."
cp $CHART_PATH/values.yaml $VALUES_FILE
cat >> $VALUES_FILE << EOF

# Prod 环境配置
replicaCount: 5

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: "2"
    memory: 2Gi

affinity:
  podAntiAffinity: hard

postgresql:
  enabled: true
  auth:
    existingSecret: dt-lite-db-secret
    secretKeys:
      adminPasswordKey: postgres-password
  primary:
    persistence:
      size: 50Gi

redis:
  enabled: true
  auth:
    existingSecret: dt-lite-redis-secret

prometheus:
  enabled: true
  scrapeInterval: 15s
EOF
echo "✅ Values 文件准备完成"
echo ""

# Step 5: Helm 部署
echo "[Step 5] Helm 部署..."
helm upgrade --install $RELEASE $CHART_PATH \
  -n $NAMESPACE \
  -f $VALUES_FILE \
  --wait \
  --timeout 600s \
  --atomic
echo "✅ Helm 部署完成"
echo ""

# Step 6: 验证部署
echo "[Step 6] 验证部署..."
echo "Pod 状态:"
kubectl get pods -n $NAMESPACE -l app=dt-lite-ai
echo ""
echo "Service 状态:"
kubectl get svc -n $NAMESPACE
echo ""
echo "资源配额:"
kubectl describe resourcequota -n $NAMESPACE
echo ""

# Step 7: Helm Test
echo "[Step 7] Helm Test..."
helm test $RELEASE -n $NAMESPACE --logs --timeout 300s
echo ""

echo "========================================"
echo "✅ Prod 环境部署完成！"
echo "========================================"
echo "Release: $RELEASE"
echo "Namespace: $NAMESPACE"
echo "Replicas: 5/5 Running"
echo "Status: DEPLOYED"
echo ""
echo "下一步：配置监控大盘和告警规则"
