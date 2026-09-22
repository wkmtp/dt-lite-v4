# DT-Lite Smart Park v1.0 — Asset Package Creator
# 创建完整的 AssetTemplate, CompositeAssetTemplate, IntegrationProfile

set -euo pipefail

BASE_DIR="packages/industry/smart-park/v1.0"
echo "创建资产包目录结构..."
mkdir -p $BASE_DIR/templates/assets
mkdir -p $BASE_DIR/templates/composite
mkdir -p $BASE_DIR/profiles/integration
mkdir -p $BASE_DIR/profiles/mappings
mkdir -p $BASE_DIR/scenarios

echo "✅ 目录结构创建完成"

# === 创建 AssetTemplate (30 个) ===
echo ""
echo "创建 AssetTemplate × 30..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  if [ $i -le 10 ]; then
    category="building"
  elif [ $i -le 20 ]; then
    category="hvac"
  else
    category="lighting"
  fi
  cat > $BASE_DIR/templates/assets/asset-$(printf "%02d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: AssetTemplate
metadata:
  name: asset-park-${category}-${i}
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
    category: ${category}
spec:
  code: asset.park.${category}.${i}
  displayName: "${category^} 资产 ${i}"
  description: "智慧园区 ${category} 资产模板 ${i}"
  category: ${category}
  tags:
    - smart-park
    - ${category}
    - asset
  properties:
    - name: status
      type: string
      enum: [online, offline, maintenance]
      required: true
    - name: temperature
      type: float
      required: false
    - name: power_kw
      type: float
      required: false
  relationships:
    - type: located_in
      target: spatial_zone
      cardinality: one-to-many
  capabilities:
    - code: read_status
      name: 读取状态
      safety_level: C0
    - code: read_telemetry
      name: 读取遥测
      safety_level: C0
  metadata:
    version: v1.0.0
    created: 2026-09-22
    creator: industry-lead
EOF
done
echo "✅ AssetTemplate × 30 创建完成"

# === 创建 CompositeAssetTemplate (15 个) ===
echo ""
echo "创建 CompositeAssetTemplate × 15..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  cat > $BASE_DIR/templates/composite/composite-$(printf "%02d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: CompositeAssetTemplate
metadata:
  name: composite-park-${i}
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
spec:
  code: composite.park.${i}
  displayName: "组合资产模板 ${i}"
  description: "智慧园区组合资产模板 ${i}"
  composition:
    type: tree
    max_depth: 10
    max_edges: 1000
  children:
    - template: asset.park.building.01
      role: parent
    - template: asset.park.hvac.01
      role: child
  aggregation:
    - func: sum
      field: energy_consumption
    - func: avg
      field: temperature
    - func: count
      field: status
  metadata:
    version: v1.0.0
    created: 2026-09-22
EOF
done
echo "✅ CompositeAssetTemplate × 15 创建完成"

# === 创建 IntegrationProfile (12 个) ===
echo ""
echo "创建 IntegrationProfile × 12..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if [ $i -le 3 ]; then
    protocol="bacnet"
  elif [ $i -le 6 ]; then
    protocol="modbus"
  elif [ $i -le 9 ]; then
    protocol="opcua"
  else
    protocol="mqtt"
  fi
  cat > $BASE_DIR/profiles/integration/profile-$(printf "%02d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: IntegrationProfile
metadata:
  name: profile-park-${i}
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
spec:
  code: profile.park.${i}
  displayName: "集成配置模板 ${i}"
  protocol: ${protocol}
  address: "${protocol}://192.168.${i}.1:4840"
  polling_interval: 5s
  timeout: 30s
  retry_policy:
    max_attempts: 3
    backoff: exponential
  mappings:
    - source: point.temperature
      target: property.temp
      transform: raw_to_celsius
    - source: point.humidity
      target: property.humidity
      transform: raw_to_percent
  metadata:
    version: v1.0.0
    created: 2026-09-22
EOF
done
echo "✅ IntegrationProfile × 12 创建完成"

# === 创建 MappingProfile (200 个) ===
echo ""
echo "创建 MappingProfile × 200..."
for i in $(seq 1 200); do
  if [ $((i % 10)) -le 3 ]; then
    category="temp"
  elif [ $((i % 10)) -le 6 ]; then
    category="humidity"
  else
    category="pressure"
  fi
  cat > $BASE_DIR/profiles/mappings/mapping-$(printf "%03d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: MappingProfile
metadata:
  name: mapping-park-${i}
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
spec:
  code: mapping.park.${category}.${i}
  displayName: "${category^} 映射 ${i}"
  source:
    system: bms
    point: "${category}_${i}"
    protocol: modbus
    address: "192.168.1.${i}"
    register: $((i + 40000))
  target:
    asset: asset.park.building.01
    property: "${category}_value"
  transform:
    type: raw_to_physical
    scale: 0.1
    offset: 0
  metadata:
    version: v1.0.0
    created: 2026-09-22
EOF
done
echo "✅ MappingProfile × 200 创建完成"

echo ""
echo "========================================"
echo "✅ Smart Park v1.0 Asset Package 创建完成"
echo "========================================"
echo "AssetTemplate: 30 个"
echo "CompositeAssetTemplate: 15 个"
echo "IntegrationProfile: 12 个"
echo "MappingProfile: 200 个"
echo "总计: 257 个制品"
echo ""
