# DT-Lite Smart Park — Performance Benchmark Script
# 执行性能基准测试

set -euo pipefail

NAMESPACE="dt-lite-prod"
SERVICE="dt-lite-smart-park-prod-ai"
HOST="localhost:8080"

echo "========================================"
echo "DT-Lite Smart Park 性能基准测试"
echo "========================================"
echo ""

# Step 1: 端口转发
echo "[Step 1] 启动端口转发..."
kubectl port-forward -n $NAMESPACE svc/$SERVICE 8080:80 &
PORTFORWARD_PID=$!
sleep 2

# Step 2: 单请求测试
echo ""
echo "[Step 2] 单请求健康检查..."
curl -w "\n时间: %{time_total}s\n状态码: %{http_code}\n" http://$HOST/health
echo ""

# Step 3: 多请求测试（使用 curl 并发）
echo "[Step 3] 并发请求测试（10 并发）..."
START_TIME=$(date +%s%N)
for i in $(seq 1 10); do
  curl -s http://$HOST/health > /dev/null &
done
wait
END_TIME=$(date +%s%N)
ELAPSED=$(( (END_TIME - START_TIME) / 1000000 ))
echo "10 并发请求完成，耗时: ${ELAPSED}ms"
echo ""

# Step 4: 资源使用监控
echo "[Step 4] 资源使用监控..."
echo "Pod 资源使用:"
kubectl top pods -n $NAMESPACE -l app=dt-lite-ai 2>/dev/null || echo "kubectl top 不可用，使用 describe"
kubectl describe pods -n $NAMESPACE -l app=dt-lite-ai 2>/dev/null | grep -E "Requests|Limits|CPU|Memory" | head -20
echo ""

echo "节点资源使用:"
kubectl top nodes 2>/dev/null || echo "kubectl top 不可用"
echo ""

# Step 5: 停止端口转发
echo "[Step 5] 停止端口转发..."
kill $PORTFORWARD_PID 2>/dev/null || true

echo ""
echo "========================================"
echo "✅ 性能基准测试完成"
echo "========================================"
echo ""
echo "建议:"
echo "1. 安装 wrk 进行更精确的压测: choco install wrk"
echo "2. 使用 kubectl top 监控资源使用"
echo "3. 访问 http://localhost:8080/metrics 查看 Prometheus metrics"
