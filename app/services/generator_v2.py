"""V2 链式生成服务：4 步调用，每步验证 + 重试，返回中间产物。"""

import json
import logging
from collections.abc import Callable, Generator

from app.llm_client import LLMClient, read_prompt
from app.models import (
    JourneyStage,
    RefineRequest,
    RefineResponse,
    StepTrace,
    V2GenerateRequest,
    V2GenerateResponse,
)

logger = logging.getLogger(__name__)


def _serialize_json(raw: dict) -> str:
    """序列化 dict 为 JSON 字符串，供 Prompt 变量替换。"""
    return json.dumps(raw, ensure_ascii=False)


def _validate_stage_list(raw: dict, min_fields: set) -> list[dict]:
    """验证 raw.stages 是否为合法列表（6~8 个），且每个元素包含最小字段集合。"""
    stages = raw.get("stages")
    if not isinstance(stages, list) or len(stages) == 0:
        raise ValueError("stages 必须是非空列表")
    if not (6 <= len(stages) <= 8):
        raise ValueError(f"stages 数量必须为 6~8，实际 {len(stages)}")
    for s in stages:
        if not isinstance(s, dict):
            raise ValueError("每个 stage 必须是 dict")
        missing = min_fields - set(s.keys())
        if missing:
            raise ValueError(f"stage 缺少字段: {missing}")
    return stages


def _check_emotion_continuity(stages: list[dict]) -> None:
    """校验情绪评分的连续性：相邻阶段差值绝对值必须 ≤ 3。"""
    scores = []
    for s in stages:
        score = s.get("emotion_score")
        if not isinstance(score, int) or not (1 <= score <= 10):
            raise ValueError(f"emotion_score 必须为 1-10 的整数，实际: {score}")
        scores.append(score)
    for i in range(1, len(scores)):
        jump = abs(scores[i] - scores[i - 1])
        if jump > 3:
            raise ValueError(
                f"情绪跳变过大: 阶段 {i}({scores[i-1]}) → 阶段 {i+1}({scores[i]}) 跳变 {jump}，"
                f"超出上限 3"
            )


def _validate_step_name_consistency(prev: list[dict], curr: list[dict]) -> None:
    """校验相邻步骤的阶段名称列表是否完全一致。"""
    prev_names = [s["phase"] for s in prev]
    curr_names = [s["phase"] for s in curr]
    if prev_names != curr_names:
        raise ValueError(f"阶段名称不一致: 前一步 {prev_names} vs 当前 {curr_names}")


def generate_v2(request: V2GenerateRequest, client: LLMClient | None = None) -> V2GenerateResponse:
    llm = client or LLMClient()
    traces: list[StepTrace] = []
    vars_ = {"product": request.product, "persona": request.persona}

    # ─── Step 1: 阶段拆解 ───
    s1, s1_dict = _call_step(
        llm, "v2/step1.txt", vars_, "v2_step1",
        min_fields={"phase"}, step=1, name="阶段拆解",
    )
    traces.append(StepTrace(step=1, name="阶段拆解", output=s1_dict))
    logger.info("V2 Step 1 完成: %d 个阶段", len(s1))

    # ─── Step 2: 行为与痛点 ───
    vars_["step1_json"] = _serialize_json(s1_dict)
    s2, s2_dict = _call_step(
        llm, "v2/step2.txt", vars_, "v2_step2",
        min_fields={"phase", "behavior", "pain_point"}, step=2, name="行为与痛点",
        extra_validator=lambda stages: _validate_step_name_consistency(s1, stages),
    )
    traces.append(StepTrace(step=2, name="行为与痛点", output=s2_dict))
    logger.info("V2 Step 2 完成")

    # ─── Step 3: 情绪评分与机会点 + 情绪连续性校验 ───
    vars_["step2_json"] = _serialize_json(s2_dict)
    s3, s3_dict = _call_step(
        llm, "v2/step3.txt", vars_, "v2_step3",
        min_fields={"phase", "emotion_score", "opportunity"}, step=3, name="情绪评分与机会点",
        extra_validator=lambda stages: (
            _validate_step_name_consistency(s2, stages),
            _check_emotion_continuity(stages),
        ),
    )
    traces.append(StepTrace(step=3, name="情绪评分与机会点", output=s3_dict))
    logger.info("V2 Step 3 完成: 情绪序列 %s", [s["emotion_score"] for s in s3])

    # ─── Step 4: 汇总 + Mermaid ───
    vars_["step3_json"] = _serialize_json(s3_dict)
    s4_dict = _call_step4(llm, "v2/step4.txt", vars_, step=4, name="汇总与图表")
    final_stages = _validate_stage_list(
        s4_dict, {"phase", "behavior", "emotion_score", "pain_point", "opportunity"}
    )
    traces.append(StepTrace(step=4, name="汇总与图表", output=s4_dict))
    logger.info("V2 Step 4 完成: %d 个阶段", len(final_stages))

    return V2GenerateResponse(
        stages=[JourneyStage.model_validate(s) for s in final_stages],
        summary=s4_dict.get("summary", ""),
        mermaid_code=s4_dict.get("mermaid_code", ""),
        traces=traces,
    )


def _call_step(
    llm: LLMClient,
    prompt_file: str,
    variables: dict,
    step_key: str,
    min_fields: set,
    step: int,
    name: str,
    max_retries: int = 2,
    extra_validator: Callable[[list[dict]], None] | None = None,
) -> tuple[list[dict], dict]:
    """通用步骤：调用 LLM，验证字段 + 可选额外校验，失败触发重试。"""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            prompt = read_prompt(prompt_file, variables)
            raw = llm.complete_json(prompt, retries=1, step=step_key)
            stages = _validate_stage_list(raw, min_fields)
            if extra_validator:
                extra_validator(stages)
            return stages, raw
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                logger.warning("V2 Step %d (%s) 第 %d 次失败，重试: %s", step, name, attempt + 1, exc)
    raise RuntimeError(f"V2 Step {step} ({name}) 失败，已重试 {max_retries} 次：{last_error}")


def refine_journey(request: RefineRequest, client: LLMClient | None = None) -> RefineResponse:
    """人工纠偏：固定前 N 个阶段 + 用户修改后的阶段，用 AI 重新生成后续阶段。

    逻辑：
    1. 提取 stages[0..modified_index]（含用户修改值）作为固定数据
    2. 提取 stages[modified_index+1..] 的 stage 名称和行为作为待续骨架
    3. 调用 AI 仅填充 emotion_score 和 opportunity
    4. 拼装完整 stages + 重新生成 summary 与 mermaid_code
    """
    llm = client or LLMClient()
    stages = request.stages
    idx = request.modified_index

    if idx < 0 or idx >= len(stages):
        raise ValueError(f"modified_index {idx} 超出范围 0~{len(stages) - 1}")

    # ─── 1. 构建固定数据 ───
    fixed_stages = []
    for i in range(idx + 1):
        s = stages[i].model_dump()
        if i == idx:
            s["emotion_score"] = request.modified_emotion_score
            s["pain_point"] = request.modified_pain_point
        fixed_stages.append(s)

    anchor_score = request.modified_emotion_score
    remaining_count = len(stages) - (idx + 1)

    # 如果修改的是最后一个阶段，无需 AI 介入，直接返回
    if remaining_count == 0:
        return RefineResponse(
            stages=[JourneyStage.model_validate(s) for s in fixed_stages],
            summary="已更新最后一个阶段。",
            mermaid_code="",
        )

    # ─── 2. 构建 AI 输入：待续阶段的 phase/behavior ───
    remaining_skeletons = []
    for i in range(idx + 1, len(stages)):
        s = stages[i].model_dump()
        remaining_skeletons.append({
            "phase": s["phase"],
            "behavior": s["behavior"],
        })

    modified_block = f"""
## 用户修改的阶段（第 {idx + 1} 个阶段，已确认）

- 阶段名称：{stages[idx].phase}
- 用户行为：{stages[idx].behavior}
- **情绪评分**：{request.modified_emotion_score}/10 ← 用户设定
- **痛点**：{request.modified_pain_point} ← 用户设定
- 机会点：{stages[idx].opportunity}

以下 {remaining_count} 个阶段需要 AI 重新生成情绪评分和机会点：

{json.dumps(remaining_skeletons, ensure_ascii=False, indent=2)}
"""

    prompt_vars = {
        "product": request.product,
        "persona": request.persona,
        "fixed_count": str(idx + 1),
        "fixed_stages_json": json.dumps(fixed_stages, ensure_ascii=False, indent=2),
        "modified_stage_block": modified_block,
        "anchor_score": str(anchor_score),
        "remaining_count": str(remaining_count),
    }

    # ─── 3. 调用 AI（带重试） ───
    last_error = None
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            prompt = read_prompt("v2/refine.txt", prompt_vars)
            raw = llm.complete_json(prompt, retries=1, step="v2_refine")
            new_tail = _validate_stage_list(raw, {"phase", "emotion_score", "opportunity"})
            if len(new_tail) != remaining_count:
                raise ValueError(f"AI 返回 {len(new_tail)} 个阶段，期望 {remaining_count}")

            # ─── 4. 拼装完整 stages ───
            merged = list(fixed_stages)
            for i, nt in enumerate(new_tail):
                merged.append({
                    "phase": remaining_skeletons[i]["phase"],
                    "behavior": remaining_skeletons[i]["behavior"],
                    "emotion_score": nt["emotion_score"],
                    "pain_point": stages[idx + 1 + i].pain_point,  # 保持原痛点
                    "opportunity": nt["opportunity"],
                })

            # ─── 5. 验证前后情绪连续性 ───
            # 检查 fixed 最后一个 → 新生成第一个
            all_scores = [fixed_stages[-1]["emotion_score"]] + [s["emotion_score"] for s in new_tail]
            for i in range(1, len(all_scores)):
                jump = abs(all_scores[i] - all_scores[i - 1])
                if jump > 3:
                    raise ValueError(
                        f"AI 生成的阶段 {idx + 1 + i} 情绪分 {all_scores[i]} "
                        f"与前一阶段 {all_scores[i-1]} 跳变 {jump}，超出上限 3"
                    )

            # ─── 6. 生成新的 summary + mermaid ───
            summary_lines = [
                f"用户手动纠正了「{merged[idx]['phase']}」阶段：",
                f"- 情绪评分调整为 {request.modified_emotion_score}/10",
            ]
            if request.modified_pain_point != stages[idx].pain_point:
                summary_lines.append(f"- 痛点更新为「{request.modified_pain_point}」")
            summary_lines.append(f"AI 已自动重新生成后续 {remaining_count} 个阶段的情绪与机会点。")
            summary = "；".join(summary_lines)

            # 生成简单 mermaid
            mermaid = "xychart-beta\n"
            mermaid += f'    title "{request.product} 用户情绪曲线（纠偏后）"\n'
            mermaid += "    x-axis ["
            mermaid += ", ".join(f'"{s["phase"]}"' for s in merged)
            mermaid += "]\n"
            mermaid += "    y-axis 1 --> 10\n"
            mermaid += "    line ["
            mermaid += ", ".join(str(s["emotion_score"]) for s in merged)
            mermaid += "]\n"

            return RefineResponse(
                stages=[JourneyStage.model_validate(s) for s in merged],
                summary=summary,
                mermaid_code=mermaid,
            )
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                logger.warning("Refine 第 %d 次失败，重试: %s", attempt + 1, exc)

    raise RuntimeError(f"纠偏失败（已重试 {max_retries} 次）: {last_error}")


def generate_v2_stream(request: V2GenerateRequest, client: LLMClient | None = None) -> Generator[dict, None, None]:
    """V2 链式生成器的流式版本：每个步骤完成后立即 yield 中间结果。

    yield 格式（与前端约定）:
        {"step": 1, "content": "正在拆解用户阶段...", "data": {"stages": [...]}}
        {"step": 2, "content": "正在分析用户行为与痛点...", "data": {...}}
        {"step": 3, "content": "正在评估情绪曲线与机会点...", "data": {...}}
        {"step": 4, "content": "正在生成汇总与图表...", "data": {...}}
        {"type": "done", "result": V2GenerateResponse}
        {"type": "error", "message": "..."}
    """
    llm = client or LLMClient()
    vars_ = {"product": request.product, "persona": request.persona}

    try:
        # ─── Step 1 ───
        yield {"step": 1, "content": f"正在为用户画像「{request.persona}」拆解 {request.product} 的体验阶段...", "data": None}
        s1, s1_dict = _call_step(
            llm, "v2/step1.txt", vars_, "v2_step1",
            min_fields={"phase"}, step=1, name="阶段拆解",
        )
        phase_names = [s["phase"] for s in s1]
        yield {"step": 1, "content": f"阶段拆解完成，识别出 {len(s1)} 个阶段：{' → '.join(phase_names)}", "data": {"stages": [{"phase": p} for p in phase_names]}}
        logger.info("V2 Stream Step 1 完成: %d 个阶段", len(s1))

        # ─── Step 2 ───
        yield {"step": 2, "content": "正在逐阶段分析用户行为与痛点...", "data": None}
        vars_["step1_json"] = _serialize_json(s1_dict)
        s2, s2_dict = _call_step(
            llm, "v2/step2.txt", vars_, "v2_step2",
            min_fields={"phase", "behavior", "pain_point"}, step=2, name="行为与痛点",
            extra_validator=lambda stages: _validate_step_name_consistency(s1, stages),
        )
        yield {"step": 2, "content": f"已完成 {len(s2)} 个阶段的行为与痛点分析", "data": {"stages": [{"phase": s["phase"], "behavior": s["behavior"], "pain_point": s["pain_point"]} for s in s2]}}
        logger.info("V2 Stream Step 2 完成")

        # ─── Step 3 ───
        yield {"step": 3, "content": "正在评估每个阶段的情绪评分与机会点...", "data": None}
        vars_["step2_json"] = _serialize_json(s2_dict)
        s3, s3_dict = _call_step(
            llm, "v2/step3.txt", vars_, "v2_step3",
            min_fields={"phase", "emotion_score", "opportunity"}, step=3, name="情绪评分与机会点",
            extra_validator=lambda stages: (
                _validate_step_name_consistency(s2, stages),
                _check_emotion_continuity(stages),
            ),
        )
        emo_seq = [s["emotion_score"] for s in s3]
        peak = max(emo_seq)
        valley = min(emo_seq)
        yield {"step": 3, "content": f"情绪曲线评估完成：序列 {' → '.join(str(x) for x in emo_seq)}，波峰 {peak}、波谷 {valley}，连续性校验通过", "data": {"stages": [{"phase": s["phase"], "emotion_score": s["emotion_score"], "opportunity": s["opportunity"]} for s in s3]}}
        logger.info("V2 Stream Step 3 完成: 情绪序列 %s", emo_seq)

        # ─── Step 4 ───
        yield {"step": 4, "content": "正在汇总所有分析结果并生成 Mermaid 情绪曲线图表...", "data": None}
        vars_["step3_json"] = _serialize_json(s3_dict)
        s4_dict = _call_step4(llm, "v2/step4.txt", vars_, step=4, name="汇总与图表")
        final_stages = _validate_stage_list(
            s4_dict, {"phase", "behavior", "emotion_score", "pain_point", "opportunity"}
        )
        yield {"step": 4, "content": f"汇总完成：{len(final_stages)} 个阶段，情绪曲线已生成，旅程地图就绪", "data": {"summary": s4_dict.get("summary", ""), "mermaid_code": s4_dict.get("mermaid_code", "")}}
        logger.info("V2 Stream Step 4 完成: %d 个阶段", len(final_stages))

        # ─── 完成 ───
        result = V2GenerateResponse(
            stages=[JourneyStage.model_validate(s) for s in final_stages],
            summary=s4_dict.get("summary", ""),
            mermaid_code=s4_dict.get("mermaid_code", ""),
            traces=[
                StepTrace(step=1, name="阶段拆解", output=s1_dict),
                StepTrace(step=2, name="行为与痛点", output=s2_dict),
                StepTrace(step=3, name="情绪评分与机会点", output=s3_dict),
                StepTrace(step=4, name="汇总与图表", output=s4_dict),
            ],
        )
        yield {"type": "done", "result": result.model_dump(mode="json")}

    except Exception as exc:
        logger.error("V2 Stream 失败: %s", exc)
        yield {"type": "error", "message": str(exc)}


def _call_step4(
    llm: LLMClient,
    prompt_file: str,
    variables: dict,
    step: int,
    name: str,
    max_retries: int = 2,
) -> dict:
    """Step 4 专用：验证顶层字段 stages+summary+mermaid_code。"""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            prompt = read_prompt(prompt_file, variables)
            raw = llm.complete_json(prompt, retries=1, step="v2_step4")
            # 顶层字段校验
            for key in ("stages", "summary", "mermaid_code"):
                if key not in raw:
                    raise ValueError(f"缺少顶层字段: {key}")
            if not isinstance(raw["stages"], list) or len(raw["stages"]) == 0:
                raise ValueError("stages 必须是非空列表")
            return raw
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                logger.warning("V2 Step %d (%s) 第 %d 次失败，重试: %s", step, name, attempt + 1, exc)
    raise RuntimeError(f"V2 Step {step} ({name}) 失败，已重试 {max_retries} 次：{last_error}")
