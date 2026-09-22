#!/bin/bash
# 验证 Smart Park v1.0 Asset Package
# 检查所有制品是否创建成功

set -euo pipefail

BASE_DIR="packages/industry/smart-park/v1.0"

echo "========================================"
echo "Smart Park v1.0 Asset Package 验证"
echo "========================================"
echo ""

# 统计各类制品数量
ASSET_COUNT=$(find $BASE_DIR/templates/assets -name "*.yaml" 2>/dev/null | wc -l)
COMPOSITE_COUNT=$(find $BASE_DIR/templates/composite -name "*.yaml" 2>/dev/null | wc -l)
INTEGRATION_COUNT=$(find $BASE_DIR/profiles/integration -name "*.yaml" 2>/dev/null | wc -l)
MAPPING_COUNT=$(find $BASE_DIR/profiles/mappings -name "*.yaml" 2>/dev/null | wc -l)
SCENARIO_COUNT=$(find $BASE_DIR/scenarios -name "*.yaml" 2>/dev/null | wc -l)

TOTAL=$((ASSET_COUNT + COMPOSITE_COUNT + INTEGRATION_COUNT + MAPPING_COUNT + SCENARIO_COUNT))

echo "制品统计:"
echo "  AssetTemplate:            $ASSET_COUNT (目标: ≥30)"
echo "  CompositeAssetTemplate:   $COMPOSITE_COUNT (目标: ≥15)"
echo "  IntegrationProfile:       $INTEGRATION_COUNT (目标: ≥12)"
echo "  MappingProfile:           $MAPPING_COUNT (目标: ≥200)"
echo "  ScenarioTemplate:         $SCENARIO_COUNT (目标: 10)"
echo "  总计:                     $TOTAL"
echo ""

# 验证验收标准
PASS=true

if [ $ASSET_COUNT -lt 30 ]; then
  echo "❌ AssetTemplate 不足 30 个"
  PASS=false
fi

if [ $COMPOSITE_COUNT -lt 15 ]; then
  echo "❌ CompositeAssetTemplate 不足 15 个"
  PASS=false
fi

if [ $INTEGRATION_COUNT -lt 12 ]; then
  echo "❌ IntegrationProfile 不足 12 个"
  PASS=false
fi

if [ $MAPPING_COUNT -lt 200 ]; then
  echo "❌ MappingProfile 不足 200 个"
  PASS=false
fi

if [ $SCENARIO_COUNT -lt 10 ]; then
  echo "❌ ScenarioTemplate 不足 10 个"
  PASS=false
fi

echo ""
if [ "$PASS" = true ]; then
  echo "✅ 所有验收标准通过！"
  echo "========================================"
  exit 0
else
  echo "❌ 部分验收标准未通过"
  echo "========================================"
  exit 1
fi
