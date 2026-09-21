# P0-04 任务书：Smart Park v1.0 Asset Package 完整打包

**负责人**：Industry Lead + DevOps  
**截止**：Day 5 (Sep 22)  
**优先级**：P0

## 交付路径

```
packages/industry/smart-park/v1.0/
├── asset-package.yaml          # Manifest v4.0
├── templates/
│   ├── assets/                 # ≥20 个 AssetTemplate
│   └── composite/              # ≥10 个 CompositeAssetTemplate
├── profiles/
│   ├── integration/            # ≥8 个 IntegrationProfile
│   └── mappings/               # ≥200 个 MappingProfile
├── scenarios/
│   └── gs-01~10/               # 10 个 Golden Scenario
├── helm/
│   └── values-smart-park.yaml  # Helm values
└── release-smart-park-v1.0.sh  # 发布脚本
```

## 制品清单

| # | 制品 | 数量/规格 | 来源 | 交付路径 |
|---|------|-----------|------|----------|
| 1 | `asset-package.yaml` | 1 份 (Manifest v4.0) | Freeze Report §Package Directory Structure | `packages/smart-park/v1.0/asset-package.yaml` |
| 2 | AssetTemplate | ≥ 20 个 | Freeze Report §Smart Park Production Baseline (15 类最小量 + 扩展) | `packages/smart-park/v1.0/templates/assets/` |
| 3 | CompositeAssetTemplate | ≥ 10 个 | Freeze Report §Composite Asset (Tree + Graph) | `packages/smart-park/v1.0/templates/composite/` |
| 4 | IntegrationProfile | ≥ 8 个 | Freeze Report §External Integration Model (BACnet/Modbus/OPC UA/MQTT/REST/OCPP) | `packages/smart-park/v1.0/profiles/integration/` |
| 5 | MappingProfile | ≥ 200 个 | Freeze Report §Point/Mapping (200+ 映射规则) | `packages/smart-park/v1.0/profiles/mappings/` |
| 6 | ScenarioTemplate | 10 个 (GS-01~10) | Freeze Report §Golden Scenarios | `packages/smart-park/v1.0/scenarios/` |
| 7 | `values-smart-park.yaml` | 1 份 | Freeze Report §Helm Deployment | `packages/smart-park/v1.0/helm/values-smart-park.yaml` |
| 8 | `release-smart-park-v1.0.sh` | 1 份 | 自编发布脚本 | `packages/smart-park/v1.0/release-smart-park-v1.0.sh` |

## Day 5 (Sep 22) 交付标准

| # | 验收标准 | 验证方式 |
|---|----------|----------|
| 1 | 全部制品入库 | `ls packages/smart-park/v1.0/` 确认 |
| 2 | `helm lint` 通过 | `helm lint packages/smart-park/v1.0/helm/` → OK |
| 3 | `kubeval` 通过 | `kubeval packages/smart-park/v1.0/helm/templates/*.yaml` → OK |
| 4 | 4 环境各渲染 1 次无报错 | `helm template` × 4 环境 |
| 5 | contract-diff 通过 | 无 contracts/universal/ 变更 → 自动 PASS |
| 6 | GS-01~10 全部可执行 | ScenarioRunner 验证 |

## 4 环境渲染命令

```bash
# Dev
helm template dt-lite-smart-park-dev packages/smart-park/v1.0/helm/ \
  -n dt-lite-dev -f packages/smart-park/v1.0/helm/values-smart-park.yaml > /tmp/dev-render.yaml

# Staging
helm template dt-lite-smart-park-staging packages/smart-park/v1.0/helm/ \
  -n dt-lite-staging -f packages/smart-park/v1.0/helm/values-smart-park.yaml > /tmp/staging-render.yaml

# Pre-Prod
helm template dt-lite-smart-park-preprod packages/smart-park/v1.0/helm/ \
  -n dt-lite-preprod -f packages/smart-park/v1.0/helm/values-smart-park.yaml > /tmp/preprod-render.yaml

# Prod
helm template dt-lite-smart-park-prod packages/smart-park/v1.0/helm/ \
  -n dt-lite-prod -f packages/smart-park/v1.0/helm/values-smart-park.yaml > /tmp/prod-render.yaml
```

## 发布脚本模板

```bash
#!/bin/bash
set -euo pipefail
# release-smart-park-v1.0.sh
ENV=$1  # dev|staging|preprod|prod
helm upgrade --install dt-lite-smart-park-$ENV packages/smart-park/v1.0/helm/ \
  -n dt-lite-$ENV \
  -f packages/smart-park/v1.0/helm/values-smart-park.yaml \
  --wait --timeout 600s
helm test dt-lite-smart-park-$ENV -n dt-lite-$ENV --logs
```

## 关联文档

- Freeze Report §Package Directory Structure
- UAA-05~UAA-09 Final Reports (各模板来源)
- Golden Assets/Scenarios 定义 (`packages/industry/smart-park/golden_assets.py`)
