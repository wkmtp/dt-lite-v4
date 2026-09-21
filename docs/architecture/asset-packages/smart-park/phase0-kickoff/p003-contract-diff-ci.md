# P0-03 任务书：contract-diff CI Job 开发接入

**负责人**：Platform Lead  
**截止**：Day 3 (Sep 19)  
**优先级**：P0

## 触发条件

PR 对 `release/uaa-v1.0-frozen` 或 `main` 提交时，且涉及 `contracts/universal/` 目录变更。

## 执行步骤

1. 检出基线 tag `v4.0.0-uaa-freeze` 的 `contracts/universal/`
2. 检出 PR 最新提交的 `contracts/universal/`
3. 运行 `python tools/contract-diff/cli.py --baseline <dir1> --target <dir2>`
4. 解析输出 JSON：`{"breaking": bool, "diffs": [...], "summary": "..."}`
5. 判定规则：
   - 存在 `REMOVED` 字段级差异 → **FAIL (Breaking)**
   - 存在 `MODIFIED` 字段级差异（非新增 optional） → **FAIL (Breaking)**
   - 仅 `ADDED` 新字段或 `MODIFIED` optional 字段 → **PASS (Non-breaking)**
   - 零差异 → **PASS**

## 工具规范

- **脚本路径**：`tools/contract-diff/cli.py`
- **输出格式**：JSON
- **CLI 参数**：
  - `--baseline`: 基准目录（tag 检出）
  - `--target`: 目标目录（PR 检出）
  - `--output`: 输出文件路径（可选）
- **单测覆盖**：≥ 90%

## CI 集成方案

**文件**：`.github/workflows/contract-diff.yml`

```yaml
name: Contract Diff Gate

on:
  pull_request:
    branches: [main, release/uaa-v1.0-frozen]
    paths:
      - 'contracts/universal/**'

jobs:
  contract-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      
      - name: Checkout baseline
        run: |
          git fetch origin v4.0.0-uaa-freeze
          mkdir -p /tmp/baseline /tmp/candidate
          git checkout v4.0.0-uaa-freeze -- contracts/universal/ -b /tmp/baseline/
          cp -r contracts/universal/ /tmp/candidate/
      
      - name: Run contract diff
        run: |
          python tools/contract-diff/cli.py \
            --baseline /tmp/baseline/universal \
            --target /tmp/candidate/universal \
            --output diff-result.json
      
      - name: Check result
        run: |
          RESULT=$(cat diff-result.json)
          if echo "$RESULT" | grep -q '"breaking": true'; then
            echo "::error::Breaking change detected in Universal Contract"
            echo "$RESULT"
            exit 1
          fi
      
      - name: Post comment on PR
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const diff = fs.readFileSync('diff-result.json', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `❌ **Contract Diff Gate FAILED**\n\nBreaking change detected:\n\`\`\`json\n${diff}\n\`\`\`\n\nAll changes to Universal Contract v1.0 must go through ARB approval and MAJOR version bump.`
            });
```

## 门禁规则

- `contract-diff / summary` 状态检查必须 **GREEN** 才能合并到 `release/uaa-v1.0-frozen`
- 保护分支已配置 Require status checks (待 Platform Lead 在 GitHub UI 确认)

## Day 3 (Sep 19) 交付清单

| # | 交付物 | 路径 |
|---|--------|------|
| 1 | `contract-diff` CLI 工具增强 + 单测 ≥90% | `tools/contract-diff/cli.py` + `tests/contract_diff/` |
| 2 | CI Workflow 文件 | `.github/workflows/contract-diff.yml` |
| 3 | 在 `release/uaa-v1.0-frozen` 上跑通一次全绿 | GitHub Actions 截图 |

## 关联文档

- Freeze Report §13.3: Contract Diff Gate
- UAA-01 Final Report §验收标准
- UAA-10 Final Report §Semantic Diff = ZERO
