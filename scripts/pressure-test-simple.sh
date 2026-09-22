#!/bin/bash
# DT-Lite Smart Park — 简化压力测试脚本
# 目标: 创建 50 个资产，验证创建成功率和耗时

ASSET_COUNT=50
NAMESPACE="dt-lite-prod"
CHART_PATH="deployment/helm/ai"

echo "========================================"
echo "DT-Lite Smart Park 压力测试"
echo "========================================"
echo "资产数量: $ASSET_COUNT"
echo "命名空间: $NAMESPACE"
echo "开始时间: $(date)"
echo "========================================"
echo ""

START_TIME=$(date +%s)

# 批量创建资产（后台执行）
echo "[1/3] 开始创建 $ASSET_COUNT 个资产..."
for i in $(seq 1 $ASSET_COUNT); do
  helm upgrade --install "asset-$i" "$CHART_PATH" \
    -n "$NAMESPACE" \
    --set replicaCount=1 \
    --set prometheus.enabled=false \
    --set postgresql.enabled=false \
    --set redis.enabled=false \
    --timeout 5s &
  
  # 每 25 个资产输出进度
  if [ $((i % 25)) -eq 0 ]; then
    echo "  进度: $i / $ASSET_COUNT"
  fi
done

# 等待所有后台任务完成
wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "[2/3] 验证资产创建结果..."
echo "  总耗时: ${DURATION} 秒"
echo ""

# 验证 Pod 状态
RUNNING_COUNT=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | grep "Running" | wc -l)
TOTAL_COUNT=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)

echo "  运行中 Pod: $RUNNING_COUNT / $TOTAL_COUNT"
echo ""

# 计算成功率
if [ "$TOTAL_COUNT" -gt 0 ]; then
  SUCCESS_RATE=$((RUNNING_COUNT * 100 / TOTAL_COUNT))
else
  SUCCESS_RATE=0
fi

echo "[3/3] 生成测试报告..."
echo ""
echo "========================================"
echo "压力测试完成"
echo "========================================"
echo "资产创建数量: $ASSET_COUNT"
echo "运行中 Pod: $RUNNING_COUNT / $TOTAL_COUNT"
echo "成功率: $SUCCESS_RATE%"
echo "总耗时: ${DURATION} 秒"
echo "完成时间: $(date)"
echo "========================================"
echo ""

# 验收标准检查
if [ "$SUCCESS_RATE" -ge 95 ]; then
  echo "✅ 验收通过: 成功率 >= 95%"
else
  echo "❌ 验收失败: 成功率 < 95%"
fi

if [ "$DURATION" -lt 600 ]; then
  echo "✅ 验收通过: 耗时 < 10 分钟"
else
  echo "❌ 验收失败: 耗时 >= 10 分钟"
fi

exit 0
