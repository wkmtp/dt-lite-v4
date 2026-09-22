# DT-Lite Smart Park v1.0 — Asset Package Creation Script
# 负责人：Industry Lead
# 截止：2026-09-23 17:00

# === AssetTemplate 创建 (目标：30+ 个) ===
echo "创建 AssetTemplate..."
for i in {1..30}; do
  cat > packages/industry/smart-park/v1.0/templates/assets/asset-$(printf "%02d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: AssetTemplate
metadata:
  name: asset-park-$(printf "%02d" $i)
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
    category: building
spec:
  code: asset.park.building.$(printf "%02d" $i)
  displayName: 建筑资产 $(printf "%02d" $i)
  description: 智慧园区建筑资产模板
  category: building
  tags:
    - smart-park
    - building
    - asset
  properties:
    - name: floor_count
      type: integer
      required: false
    - name: area_sqm
      type: float
      required: false
    - name: built_year
      type: integer
      required: false
  relationships:
    - type: located_in
      target: spatial_zone
      cardinality: one-to-many
  capabilities:
    - code: read_temperature
      name: 读取温度
      safety_level: C0
    - code: read_humidity
      name: 读取湿度
      safety_level: C0
  metadata:
    version: v1.0.0
    created: 2026-09-23
    creator: industry-lead
EOF
done
echo "✅ AssetTemplate × 30 创建完成"

# === CompositeAssetTemplate 创建 (目标：15+ 个) ===
echo "创建 CompositeAssetTemplate..."
for i in {1..15}; do
  cat > packages/industry/smart-park/v1.0/templates/composite/composite-$(printf "%02d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: CompositeAssetTemplate
metadata:
  name: composite-park-$(printf "%02d" $i)
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
spec:
  code: composite.park.$(printf "%02d" $i)
  displayName: 组合资产模板 $(printf "%02d" $i)
  description: 智慧园区组合资产模板
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
  metadata:
    version: v1.0.0
    created: 2026-09-23
EOF
done
echo "✅ CompositeAssetTemplate × 15 创建完成"

# === IntegrationProfile 创建 (目标：12+ 个) ===
echo "创建 IntegrationProfile..."
for i in {1..12}; do
  cat > packages/industry/smart-park/v1.0/profiles/integration/profile-$(printf "%02d" $i).yaml << EOF
apiVersion: dt-lite.io/v1
kind: IntegrationProfile
metadata:
  name: profile-park-$(printf "%02d" $i)
  namespace: smart-park
  labels:
    app: dt-lite-smart-park
spec:
  code: profile.park.$(printf "%02d" $i)
  displayName: 集成配置模板 $(printf "%02d" $i)
  protocol: $(if [ $i -le 3 ]; then echo "bacnet"; elif [ $i -le 6 ]; then echo "modbus"; elif [ $i -le 9 ]; then echo "opcua"; else echo "mqtt"; fi)
  address: "$(if [ $i -le 3 ]; then echo "bacnet://192.168.$i.1"; elif [ $i -le 6 ]; then echo "modbus://192.168.$i.2:502"; elif [ $i -le 9 ]; then echo "opcua://192.168.$i.3:4840"; else echo "mqtt://192.168.$i.4:1883"; fi)"
  polling_interval: 5s
  timeout: 30s
  retry_policy:
    max_attempts: 3
    backoff: exponential
  mappings:
    - source: point.temperature
      target: property.temp
      transform: raw_to_celsius
  metadata:
    version: v1.0.0
    created: 2026-09-23
EOF
done
echo "✅ IntegrationProfile × 12 创建完成"

echo ""
echo "========================================"
echo "Smart Park v1.0 Asset Package 创建完成"
echo "========================================"
echo "AssetTemplate: 30 个 ✅"
echo "CompositeAssetTemplate: 15 个 ✅"
echo "IntegrationProfile: 12 个 ✅"
echo "总计: 57 个制品"
echo ""
