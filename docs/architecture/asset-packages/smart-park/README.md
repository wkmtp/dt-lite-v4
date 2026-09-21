# DT-Lite V4.0 Universal Asset Assembly Contract v1.0
## Contract Hardening Engineering Package

本工程包包含：

```text
00_UAA_Contract_Hardening_and_Freeze_Specification.md
UAA-01_AgnesCode_Execution_Prompt.md
UAA-02_AgnesCode_Execution_Prompt.md
UAA-03_AgnesCode_Execution_Prompt.md
UAA-04_AgnesCode_Execution_Prompt.md
UAA-05_AgnesCode_Execution_Prompt.md
UAA-06_AgnesCode_Execution_Prompt.md
UAA-07_AgnesCode_Execution_Prompt.md
UAA-08_AgnesCode_Execution_Prompt.md
UAA-09_AgnesCode_Execution_Prompt.md
UAA-10_AgnesCode_Execution_Prompt.md
```

执行顺序：

```text
UAA-01
 ↓
Architecture Review
 ↓
UAA-02
 ↓
Architecture Review
 ↓
...
 ↓
UAA-09
 ↓
UAA-10
 ↓
FINAL FREEZE
```

最高优先级原则：

```text
Universal Asset Assembly Contract v1.0
                >
Smart Park Requirements
                >
Smart Factory Requirements
                >
Specific Project Requirements
```

Factory Compatibility 的目标不是“让 Factory 跑起来就算成功”，而是证明：

```text
Smart Park
     +
Smart Factory
     ↓
same Universal Contract
same Assembly Semantics
same Zero-Code Assembly Engine
```

并满足：

```text
Universal Contract semantic diff = ZERO
```

如果 Factory 必须通过修改 Universal Contract 才能实现，则说明 Contract 尚未真正冻结，UAA-10 必须 FAIL。
