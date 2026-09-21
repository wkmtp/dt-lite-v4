# Contract Diff CI Workflow 设计文档

**负责人**: Platform Lead
**截止**: Day 2 (Sep 22) 15:00
**优先级**: P0

---

## 🎯 目标

创建 `.github/workflows/contract-diff.yml`，在 PR 合并前自动检测 Universal Contract Breaking Changes。

---

## 📋 Workflow 配置

### **触发条件**
```yaml
on:
  pull_request:
    branches: [main, release/uaa-v1.0-frozen]
    paths:
      - 'contracts/universal/**'
  push:
    branches: [release/uaa-v1.0-frozen]
    paths:
      - 'contracts/universal/**'
```

### **Job 配置**
```yaml
jobs:
  contract-diff:
    name: Contract Diff Gate
    runs-on: ubuntu-latest
    timeout-minutes: 10
```

---

## 🔧 执行步骤

### **Step 1: Checkout 代码**
```yaml
- name: Checkout PR code
  uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}
    fetch-depth: 0
```

### **Step 2: 检出基线**
```yaml
- name: Checkout baseline
  run: |
    git fetch origin v4.0.0-uaa-freeze
    mkdir -p /tmp/baseline /tmp/candidate
    git checkout v4.0.0-uaa-freeze -- contracts/universal/
    cp -r contracts/universal/ /tmp/baseline/
```

### **Step 3: 运行 Contract Diff**
```yaml
- name: Run contract diff
  run: |
    python tools/contract-diff/cli.py \
      --baseline /tmp/baseline/universal \
      --target contracts/universal \
      --output diff-result.json \
      --verbose

- name: Upload diff result
  uses: actions/upload-artifact@v4
  with:
    name: contract-diff-result
    path: diff-result.json
```

### **Step 4: 检查 Breaking Changes**
```yaml
- name: Check for breaking changes
  id: check
  run: |
    RESULT=$(cat diff-result.json)
    echo "Result: $RESULT"
    
    if echo "$RESULT" | grep -q '"breaking": true'; then
      echo "BREAKING=true" >> $GITHUB_ENV
      echo "::error::Breaking change detected in Universal Contract"
    else
      echo "BREAKING=false" >> $GITHUB_ENV
    fi
    
    # 输出摘要
    SUMMARY=$(echo "$RESULT" | jq -r '.summary')
    echo "Summary: $SUMMARY" >> $GITHUB_STEP_SUMMARY
  shell: bash
```

### **Step 5: 发布 PR 评论（Breaking 时）**
```yaml
- name: Post comment on PR
  if: env.BREAKING == 'true' && github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const diff = fs.readFileSync('diff-result.json', 'utf8');
      const result = JSON.parse(diff);
      
      let comment = `❌ **Contract Diff Gate FAILED**\n\n`;
      comment += `**Summary**: ${result.summary}\n\n`;
      comment += `**Statistics**:\n`;
      comment += `- Added: ${result.statistics.added}\n`;
      comment += `- Removed: ${result.statistics.removed}\n`;
      comment += `- Modified: ${result.statistics.modified}\n\n`;
      comment += `All changes to Universal Contract v1.0 must go through ARB approval and MAJOR version bump.\n\n`;
      comment += `See [Architecture Governance](../../wiki/Architecture-Governance) for details.`;
      
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: comment
      });
```

---

## 🚪 门禁规则

### **合并条件**
- `contract-diff / summary` 状态检查必须 **GREEN**
- 保护分支 `release/uaa-v1.0-frozen` 已配置 Require status checks

### **Breaking Change 处理流程**
```
1. CI 检测到 Breaking Change
2. PR 自动添加评论说明
3. PR 合并被阻断
4. 开发者提交 Architecture Conflict Report
5. ARB 审批通过
6. Universal Contract MAJOR 版本发布
7. 重新运行 CI
```

---

## 🧪 测试策略

### **本地测试**
```bash
# 测试无差异场景
python tools/contract-diff/cli.py \
  --baseline contracts/universal/ \
  --target contracts/universal/ \
  --output test-result.json

# 验证输出
cat test-result.json | jq '.breaking'  # 应为 false
```

### **CI 测试**
- 每次 PR 自动触发
- 仅当 `contracts/universal/**` 有变更时运行
- 结果上传为 Artifact

---

## 📊 监控与告警

### **Metrics**
- Workflow 执行时间（目标：< 2 min）
- Breaking Change 检测率
- PR 阻断次数

### **告警**
- Workflow 失败 > 5 次/周 → 通知 Platform Lead
- Breaking Change 检测 → 自动评论 PR + 通知 ARB

---

## 📎 关联文档

- `tools/contract-diff/DESIGN.md`
- Freeze Report §13.3: Contract Diff Gate
- UAA-01 Final Report §验收标准

---

**文档版本**: v1.0
**创建时间**: 2026-09-21 20:00
**负责人**: Platform Lead (dt_manager 代理)
