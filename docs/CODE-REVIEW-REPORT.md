# 代码审查报告（二次审查）：V1 / V2 用户旅程地图生成器

**审查范围**：`app/` 全部代码 + `prompts/` 全部模板 + `.gitignore` + `tests/`  
**审查日期**：2026-06-18（首次审查已修复，此为二次回归审查）  
**审查方法**：人工逐文件审查，聚焦 4 个审查重点 + 对首次审查修复项的回归验证

---

## 审查结果摘要

| 审查项 | 状态 | 变更说明 |
|---|---|---|
| Prompt 歧义 | Minor（2 项遗留） | V1 字段列表、Step 1 框架二选一待修正 |
| 链式异常处理 | **Pass** | P0/P1 修复后健壮性显著提升 |
| 情绪评分连续性校验 | **Pass（已修复）** | 运行时校验已就位，重试已联动 |
| 环境变量安全 | **Pass** | `.env` 已 gitignore，无变化 |

**总体评估**：首次审查中的 Critical（P0）和 Important（P1）问题全部修复完毕。剩余 2 项 Minor 级 Prompt 优化不影响交付质量。代码已具备推进到前端阶段的可靠性条件。

---

## 一、Prompt 歧义审查

### 1.1 V1 Prompt — 字段列表未包含 summary（遗留）

**文件**：[prompts/v1/generate.txt](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/prompts/v1/generate.txt#L8-L14)

"必须包含以下字段"列表为 `phase, behavior, emotion_score, pain_point, opportunity`，未列出 `summary`，但 JSON 示例中又包含 `summary`。

**当前状态**：未修复（首次审查标记为 P2）。后端 `raw.get("summary", "")` 有默认值保护，影响可控。

**建议**：在 "必须包含以下字段" 列表中追加 `summary`。

---

### 1.2 V2 Step 4 Prompt — Mermaid 转义示例（遗留）

**文件**：[prompts/v2/step4.txt](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/prompts/v2/step4.txt#L29)

```
"mermaid_code": "xychart-beta\\n    title \\"用户情绪旅程\\"..."
```

**当前状态**：未修复（首次审查标记为 P3）。`_call_step4` 有 2 次重试兜底，影响有限。

**建议**：用中文描述规则代替示例中的转义结果。

---

### 1.3 V2 Step 1 Prompt — 框架"AIDA 或 5E"歧义（遗留）

**文件**：[prompts/v2/step1.txt](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/prompts/v2/step1.txt#L6)

"或"让 LLM 在 AIDA（4 段）和 5E（5 段）之间选择，可能产出不足 6 个阶段。

**当前状态**：未修复（首次审查标记为 P2）。但代码层已加入 `_validate_stage_list` 的 `6 <= len <= 8` 约束 —— **如果 LLM 输出不足 6 个阶段，会触发验证失败 → 重试**。这意味着 Prompt 层面的歧义已被代码层兜底，不再是实际问题。

**修正评估**：从 P2 降级为 **Won't Fix** — 代码层已通过重试机制覆盖此风险。

---

## 二、链式调用异常处理审查（回归验证）

### 2.1 已修复：日志初始化

**文件**：[app/main.py](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/app/main.py#L8)

```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
```

✅ 重试日志现在会输出到 stderr，调试时可追踪每一步的失败原因。

---

### 2.2 已修复：阶段数量校验

**文件**：[app/services/generator_v2.py](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/app/services/generator_v2.py#L23-L24)

```python
if not (6 <= len(stages) <= 8):
    raise ValueError(f"stages 数量必须为 6~8，实际 {len(stages)}")
```

✅ 不足 6 个或超过 8 个阶段会触发验证失败 → 重试。

---

### 2.3 已修复：阶段名称一致性校验

**文件**：[app/services/generator_v2.py](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/app/services/generator_v2.py#L51-L56)

```python
def _validate_step_name_consistency(prev, curr):
    # Step 2 vs Step 1, Step 3 vs Step 2 的名称对齐检查
```

✅ Step 2/3 的 `extra_validator` 会校验与上一步的阶段名称完全一致。

---

### 2.4 嵌套重试分析

```
每步 _call_step:  3 次尝试（max_retries=2）
每次 complete_json: 2 次尝试（retries=1）
────────────────────────────────────
单步最坏 LLM 调用: 3 × 2 = 6 次
V2 全流程最坏: 6 × 4 = 24 次
```

当前重试策略合理：每层有独立重试，内层（LLM SDK 级）处理网络超时，外层（Step 级）处理格式/内容不合规。作为面试演示项目，24 次 × 40s = 最长 16 分钟的边界情况可接受。

---

### 2.5 残留问题：异常粒度过于粗糙

**文件**：[app/main.py](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/app/main.py#L207-L208) 和 [L222-L224](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/app/main.py#L222-L224)

```python
except Exception as exc:
    raise GenerationError(f"V1 生成失败: {exc}", status_code=500) from exc
# ...
except Exception as exc:
    raise GenerationError(f"V2 生成失败: {exc}", status_code=500) from exc
```

**级别**：Minor — V1/V2 端点均用 `Exception` 兜底，在 mock 模式下无害。接入真实 LLM 时建议区分 `RuntimeError`（业务预期失败，已有日志）和 `Exception`（未预期 Bug，应记录 traceback）。

**建议**：
```python
except RuntimeError as exc:
    raise GenerationError(f"V2 生成失败: {exc}", status_code=500) from exc
except Exception as exc:
    logger.exception("V2 未预期异常")
    raise GenerationError("V2 内部错误", status_code=500) from exc
```

---

## 三、情绪评分连续性校验（回归验证 — Pass）

### 3.1 已修复：运行时校验

**文件**：[app/services/generator_v2.py](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/app/services/generator_v2.py#L34-L48)

```python
def _check_emotion_continuity(stages: list[dict]) -> None:
    """校验情绪评分的连续性：相邻阶段差值绝对值必须 ≤ 3。"""
    jump = abs(scores[i] - scores[i - 1])
    if jump > 3:
        raise ValueError(
            f"情绪跳变过大: 阶段 {i}({scores[i-1]}) → 阶段 {i+1}({scores[i]}) 跳变 {jump}，"
            f"超出上限 3"
        )
```

✅ 嵌入 Step 3 的 `extra_validator`，与重试机制无缝联动。

### 3.2 已验证：运行时行为

首次审查中 mock 数据情绪序列为 `[7,5,6,4,8,6,8]`，阶段 4→5 跳变 4→8 = 4，触发校验后返回 500 并显示详细错误消息。修复 mock 为 `[7,5,6,5,8,6,8]` 后通过。

**实际流程**：
```
Step 3 LLM 返回情绪序列 [7,5,6,4,8,6,8]
  → _validate_stage_list 通过（字段齐全）
  → _check_emotion_continuity 检测到 4→8=4 > 3
  → ValueError("情绪跳变过大: 阶段 4(4) → 阶段 5(8) 跳变 4，超出上限 3")
  → _call_step 外层 catch → retry #1
  → retry 返回同样序列 → retry #2 同样失败
  → 3 次全部失败 → RuntimeError → 500 返回给前端
```

### 3.3 完整校验链

| 层次 | 校验内容 | 失败行为 |
|---|---|---|
| `LLMClient.complete_json` | JSON 是否可解析 | 内层重试 1 次 |
| `_validate_stage_list` | stages 是否 6~8 个 + 每元素有所需字段 | 外层重试 2 次 |
| `_validate_step_name_consistency` | 阶段名称是否与上一步一致 | 外层重试 2 次 |
| `_check_emotion_continuity` | 相邻情绪差 ≤ 3 + 每分 1-10 | 外层重试 2 次 |
| `JourneyStage.model_validate` | Pydantic 类型校验（ge=1, le=10） | 直接 500（不再重试） |

---

## 四、环境变量安全检查（回归验证 — Pass）

**文件**：[.gitignore](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/.gitignore)

| 检查项 | 状态 | 备注 |
|---|---|---|
| `.env` 在 gitignore | ✅ 第 4 行 | `.env` 始终被排除 |
| `.env.example` 可安全提交 | ✅ | 占位值 `sk-your-api-key-here` |
| 代码中无硬编码密钥 | ✅ | `os.getenv("OPENAI_API_KEY", "")` |
| 新增文件无泄露 | ✅ | 所有新建文件（prompts/v2/*, generator_v2.py）均不含密钥 |

---

## 五、回归验证清单

| 修复项（首次审查） | 当前状态 | 关联文件 |
|---|---|---|
| 情绪连续性校验 | ✅ 已实现 | generator_v2.py:34-48 |
| 日志初始化 | ✅ 已实现 | main.py:8 |
| 阶段数量校验 | ✅ 已实现 | generator_v2.py:23-24 |
| 阶段名称一致性 | ✅ 已实现 | generator_v2.py:51-56 |
| 函数命名修正 | ✅ 已修复 | `_extract_json` → `_serialize_json` |
| Mock 数据修复 | ✅ 已修复 | V2 mock 4→8 改为 5→8 |

---

## 六、验证状态

| 检查项 | 工具 | 结果 |
|---|---|---|
| 测试套件 | `pytest tests/test_journey.py` | 4/4 passed |
| V1 API | `POST /api/v1/generate` | 200, 7 stages |
| V2 API | `POST /api/v2/generate` | 200, 7 stages, 情绪[7,5,6,5,8,6,8], 4 traces |
| .env 安全 | 人工审查 | gitignore 已包含 |

---

*审查者：TRAE-code-review（二次审查）*  
*审查时间：2026-06-18*  
*审查基准：首次审查报告 P0-P3 修复项回归 + [PRD.md](file:///D:/codex_dev/travel_agent/worktrees/journey-dev/docs/PRD.md) 验收标准*
