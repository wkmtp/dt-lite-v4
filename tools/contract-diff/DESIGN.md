# Contract Diff CLI 工具设计文档

**负责人**: Platform Lead
**截止**: Day 2 (Sep 22) 15:00
**优先级**: P0

---

## 🎯 目标

开发 `tools/contract-diff/cli.py` 命令行工具，用于检测 Universal Contract 的 Breaking Changes。

---

## 📋 功能需求

### **核心功能**
1. **基线检出**: 从指定 tag/branch 检出 `contracts/universal/` 目录
2. **目标检出**: 从当前工作目录获取 `contracts/universal/` 目录
3. **语义差异分析**: 对比两个目录，检测 ADDED/REMOVED/MODIFIED 字段
4. **Breaking 判定**: 根据规则判定是否为 Breaking Change
5. **JSON 输出**: 输出结构化结果供 CI 解析

### **CLI 接口**
```bash
python tools/contract-diff/cli.py \
  --baseline <dir1> \
  --target <dir2> \
  [--output <file>] \
  [--verbose]
```

### **输出格式**
```json
{
  "breaking": false,
  "summary": "No breaking changes detected",
  "diffs": [
    {
      "type": "ADDED",
      "path": "asset.park.elevator.type",
      "field": "description",
      "old_value": null,
      "new_value": "High-speed elevator"
    }
  ],
  "statistics": {
    "total_diffs": 1,
    "added": 1,
    "removed": 0,
    "modified": 0,
    "breaking_changes": 0
  }
}
```

---

## 🔍 判定规则

### **Breaking Change 规则**
| 操作 | 字段类型 | 是否 Breaking |
|------|----------|---------------|
| REMOVED | 任何 | ✅ Breaking |
| MODIFIED | required 字段 | ✅ Breaking |
| MODIFIED | optional 字段 | ❌ 非 Breaking |
| ADDED | required 字段 | ❌ 非 Breaking (向后兼容) |
| ADDED | optional 字段 | ❌ 非 Breaking |
| 无差异 | - | ❌ 非 Breaking |

### **特殊规则**
1. **枚举值修改**: 任何枚举值增减/修改 = Breaking
2. **类型变更**: 字段类型变更 = Breaking
3. **约束变更**: maxLength/minLength/pattern 等约束收紧 = Breaking
4. **嵌套对象**: 嵌套对象的 Breaking 传递到父对象

---

## 📁 目录结构

```
tools/
└── contract-diff/
    ├── __init__.py
    ├── cli.py              # CLI 入口
    ├── diff_engine.py      # 差异分析引擎
    ├── breaking_detector.py # Breaking 判定器
    ├── yaml_parser.py      # YAML 解析器
    ├── json_schema.py      # JSON Schema 处理
    └── report.py           # 报告生成器

tests/
└── contract_diff/
    ├── __init__.py
    ├── test_cli.py         # CLI 测试
    ├── test_diff_engine.py # 差异引擎测试
    ├── test_breaking_detector.py # Breaking 判定测试
    ├── test_yaml_parser.py # YAML 解析测试
    └── fixtures/           # 测试数据
        ├── baseline/
        │   ├── asset.yaml
        │   └── point.yaml
        └── candidate/
            ├── asset.yaml
            └── point.yaml
```

---

## 🧪 测试要求

### **覆盖率目标**: ≥ 90%

### **测试用例**
| 类别 | 用例数 | 覆盖场景 |
|------|--------|----------|
| 无差异 | 2 | 相同文件、空目录 |
| ADDED 字段 | 3 | optional、required、嵌套 |
| REMOVED 字段 | 3 | optional、required、嵌套 |
| MODIFIED 字段 | 4 | optional→required、类型变更、约束收紧 |
| Breaking 判定 | 5 | 各种组合场景 |
| CLI 接口 | 3 | 参数解析、输出格式、错误处理 |
| **总计** | **20+** | |

---

## 🔧 实现计划

### **Day 1 (Sep 21) — 已完成**
- [x] 设计文档编写
- [ ] 目录结构创建
- [ ] YAML 解析器实现
- [ ] 差异引擎实现

### **Day 2 (Sep 22) — 进行中**
- [ ] Breaking 判定器实现
- [ ] CLI 接口实现
- [ ] 单元测试编写
- [ ] 覆盖率验证 (≥90%)
- [ ] CI Workflow 集成

### **Day 3 (Sep 23) — 验收**
- [ ] 在 `release/uaa-v1.0-frozen` 上跑通
- [ ] GitHub Actions 截图
- [ ] 文档更新

---

## 📊 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | CLI 工具可执行 | `python tools/contract-diff/cli.py --help` |
| 2 | 输出 JSON 格式正确 | 解析输出验证 |
| 3 | Breaking 判定准确 | 20+ 测试用例全部通过 |
| 4 | 覆盖率 ≥ 90% | `pytest --cov=tools/contract-diff` |
| 5 | CI 集成成功 | GitHub Actions 绿灯 |

---

## 📎 关联文档

- Freeze Report §13.3: Contract Diff Gate
- UAA-01 Final Report §验收标准
- `.github/workflows/contract-diff.yml`

---

**文档版本**: v1.0
**创建时间**: 2026-09-21 19:55
**负责人**: Platform Lead (dt_manager 代理)
