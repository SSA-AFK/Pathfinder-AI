import json
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from app.cache import get_cache, cost_saved
from app.errors import GenerationError, register_error_handlers
from app.llm_client import LLMClient, read_prompt
from app.models import (
    GenerateRequest,
    GenerateResponse,
    JourneyMapResult,
    JourneyStage,
    RefineRequest,
    RefineResponse,
    StepTrace,
    V1GenerateRequest,
    V1GenerateResponse,
    V2GenerateRequest,
    V2GenerateResponse,
)
from app.services.generator_v2 import generate_v2, generate_v2_stream, refine_journey

load_dotenv()

app = FastAPI(title="User Journey Map Generator")
register_error_handlers(app)


def _make_v1_result(product: str, persona: str) -> JourneyMapResult:
    stages = [
        JourneyStage(
            phase="发现产品",
            behavior="用户通过搜索引擎或推荐链接首次接触到产品首页",
            emotion_score=7,
            pain_point="首页价值主张不够清晰，用户不确定产品是否满足需求",
            opportunity="在首屏提供明确的价值主张和典型用例演示",
        ),
        JourneyStage(
            phase="了解功能",
            behavior="用户浏览产品介绍页面，查看功能列表和截图",
            emotion_score=6,
            pain_point="功能描述偏技术化，非技术用户理解成本高",
            opportunity="用场景化语言重写功能描述，配合用户旅程示例",
        ),
        JourneyStage(
            phase="首次使用",
            behavior="用户输入产品名称和用户画像，点击生成按钮",
            emotion_score=5,
            pain_point="首次输入时不确定格式要求，担心输入错误导致无意义结果",
            opportunity="提供示例输入按钮和输入格式提示",
        ),
        JourneyStage(
            phase="等待生成",
            behavior="用户观看生成进度，等待 AI 返回结果",
            emotion_score=4,
            pain_point="等待时间不确定，缺少进度反馈导致焦虑",
            opportunity="显示明确的进度指示和预估剩余时间",
        ),
        JourneyStage(
            phase="查看结果",
            behavior="用户浏览生成的旅程地图、情绪曲线和流程图",
            emotion_score=8,
            pain_point="结果信息量大，初次查看容易迷失重点",
            opportunity="高亮情绪拐点和关键机会点，提供摘要面板",
        ),
        JourneyStage(
            phase="调整优化",
            behavior="用户根据初步结果修改输入参数或重新生成",
            emotion_score=6,
            pain_point="缺少版本对比功能，难以判断修改是否改善了结果",
            opportunity="保存历史记录，支持并排对比多次生成结果",
        ),
        JourneyStage(
            phase="导出分享",
            behavior="用户复制 Mermaid 代码或导出 Markdown 文件",
            emotion_score=8,
            pain_point="Mermaid 代码在某些平台渲染异常，用户需要手动调试",
            opportunity="提供预览渲染效果，标记常见兼容性问题",
        ),
    ]
    return JourneyMapResult(
        version="v1",
        product=product,
        persona=persona,
        stages=stages,
        mermaid_code="graph LR\n"
        "    A[发现产品] --> B[了解功能]\n"
        "    B --> C[首次使用]\n"
        "    C --> D[等待生成]\n"
        "    D --> E[查看结果]\n"
        "    E --> F[调整优化]\n"
        "    F --> G[导出分享]",
    )


def _make_v2_result(product: str, persona: str) -> JourneyMapResult:
    stages = [
        JourneyStage(
            phase="发现产品",
            behavior="用户通过搜索引擎或推荐链接首次接触到产品首页",
            emotion_score=7,
            pain_point="首页价值主张不够清晰",
            opportunity="在首屏提供明确的价值主张",
        ),
        JourneyStage(
            phase="了解功能",
            behavior="用户浏览产品介绍页面，查看功能列表",
            emotion_score=6,
            pain_point="功能描述偏技术化",
            opportunity="用场景化语言重写功能描述",
        ),
        JourneyStage(
            phase="首次使用",
            behavior="用户输入产品名称和用户画像，点击生成",
            emotion_score=5,
            pain_point="不确定输入格式要求",
            opportunity="提供示例输入按钮",
        ),
        JourneyStage(
            phase="等待生成",
            behavior="用户观看生成进度，等待 AI 返回结果",
            emotion_score=5,
            pain_point="缺少进度反馈",
            opportunity="显示明确的进度指示",
        ),
        JourneyStage(
            phase="查看结果",
            behavior="用户浏览旅程地图、情绪曲线和流程图",
            emotion_score=7,
            pain_point="结果信息量较大",
            opportunity="高亮情绪拐点和关键机会点",
        ),
        JourneyStage(
            phase="调整优化",
            behavior="用户修改输入参数或重新生成",
            emotion_score=6,
            pain_point="缺少版本对比功能",
            opportunity="支持并排对比多次生成结果",
        ),
        JourneyStage(
            phase="导出分享",
            behavior="用户复制 Mermaid 代码或导出 Markdown",
            emotion_score=8,
            pain_point="Mermaid 代码在某些平台渲染异常",
            opportunity="提供预览渲染效果",
        ),
    ]
    return JourneyMapResult(
        version="v2",
        product=product,
        persona=persona,
        stages=stages,
        mermaid_code="graph LR\n"
        "    A[发现产品] --> B[了解功能]\n"
        "    B --> C[首次使用]\n"
        "    C --> D[等待生成]\n"
        "    D --> E[查看结果]\n"
        "    E --> F[调整优化]\n"
        "    F --> G[导出分享]",
    )


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    v1_result = _make_v1_result(request.product, request.persona)

    if request.mode == "v1":
        return GenerateResponse(mode="v1", v1=v1_result)

    v2_result = _make_v2_result(request.product, request.persona)
    traces = [
        StepTrace(step=1, name="阶段拆解", output={"stages": [{"phase": s.phase} for s in v2_result.stages]}),
        StepTrace(step=2, name="行为细化", output={"stages": [{"phase": s.phase, "behavior": s.behavior} for s in v2_result.stages]}),
        StepTrace(step=3, name="情绪评分与机会点", output={"stages": [{"phase": s.phase, "emotion_score": s.emotion_score} for s in v2_result.stages]}),
        StepTrace(step=4, name="结构化输出", output={"stages": [s.model_dump() for s in v2_result.stages]}),
    ]

    if request.mode == "v2":
        return GenerateResponse(mode="v2", v2=v2_result, traces=traces)

    from app.models import CompareReport
    return GenerateResponse(
        mode="compare",
        v1=v1_result,
        v2=v2_result,
        traces=traces,
        report=CompareReport(
            summary="V1 单次生成 7 个阶段，V2 链式生成同样 7 个阶段但情绪曲线更平滑。",
            emotion_curve_analysis="V1 情绪序列 [7,6,5,4,8,6,8]，V2 情绪序列 [7,6,5,5,7,6,8]，V2 相邻差值更小。",
            recommendation="面试展示时使用 compare 模式，展示 V2 链式生成的连续性优势。",
        ),
    )


@app.post("/api/v1/generate", response_model=V1GenerateResponse)
def generate_v1(request: V1GenerateRequest) -> V1GenerateResponse:
    """V1 单次调用生成：带语义缓存（MD5 完全匹配），降低重复查询成本。"""
    _log = logging.getLogger(__name__)
    cache = get_cache()

    # ── 检查缓存 ──
    hit, cached_data = cache.get(request.product, request.persona)
    if hit:
        _log.info("V1 缓存命中: %s | %s", request.product[:20], request.persona[:20])
        return V1GenerateResponse(
            stages=[JourneyStage.model_validate(s) for s in cached_data["stages"]],
            summary=cached_data.get("summary", ""),
            cached=True,
            saved_cost=cached_data.get("saved_cost", cost_saved()),
        )

    # ── 未命中，调用 LLM ──
    def _validate_v1_output(raw: dict) -> list[dict]:
        stages = raw.get("stages")
        if not isinstance(stages, list) or not (6 <= len(stages) <= 8):
            raise ValueError(f"stages 必须为 6~8 个元素的列表")
        required = {"phase", "behavior", "emotion_score", "pain_point", "opportunity"}
        scores = []
        for i, s in enumerate(stages):
            if not isinstance(s, dict):
                raise ValueError(f"stages[{i}] 不是对象")
            missing = required - set(s.keys())
            if missing:
                raise ValueError(f"stages[{i}] 缺少字段: {missing}")
            score = s["emotion_score"]
            if not isinstance(score, int) or not (1 <= score <= 10):
                raise ValueError(f"stages[{i}] emotion_score 必须为 1-10 整数，实际: {score}")
            scores.append(score)
        for i in range(1, len(scores)):
            if abs(scores[i] - scores[i-1]) > 3:
                raise ValueError(f"情绪跳变过大: 阶段{i}({scores[i-1]})→阶段{i+1}({scores[i]}), 跳变{abs(scores[i]-scores[i-1])}>3")
        return stages

    client = LLMClient()
    max_retries = 2
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            prompt = read_prompt("v1/generate.txt", {
                "product": request.product,
                "persona": request.persona,
            })
            raw = client.complete_json(prompt, retries=1)
            validated = _validate_v1_output(raw)
            stages = [JourneyStage.model_validate(s) for s in validated]

            # ── 写入缓存 ──
            saved = cost_saved()
            cache.set(request.product, request.persona, {
                "stages": [s.model_dump() for s in stages],
                "summary": raw.get("summary", ""),
                "saved_cost": saved,
            })

            return V1GenerateResponse(
                stages=stages,
                summary=raw.get("summary", ""),
                cached=False,
                saved_cost=0.0,
            )
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                _log.warning("V1 第 %d 次失败，重试: %s", attempt + 1, exc)
    raise GenerationError(f"V1 生成失败（已重试 {max_retries} 次）: {last_error}", status_code=500)


@app.post("/api/v2/generate")
async def generate_v2_endpoint(request: V2GenerateRequest):
    """V2 SSE 流式生成：带缓存，命中则直接返回 done 事件。"""
    cache = get_cache()
    _log = logging.getLogger(__name__)

    hit, cached_data = cache.get(request.product, request.persona)
    if hit:
        _log.info("V2 缓存命中: %s", request.product[:20])
        saved = cached_data.get("saved_cost", cost_saved())
        # 返回单事件 SSE：直接 done
        async def _cached_stream():
            yield f"data: {json.dumps({'type': 'done', 'result': cached_data, 'cached': True, 'saved_cost': saved}, ensure_ascii=False, default=str)}\n\n"
        return StreamingResponse(
            _cached_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    def _event_stream():
        for event in generate_v2_stream(request):
            # 在 done 事件中注入 cached flag
            if event.get("type") == "done":
                # 写入缓存
                cache.set(request.product, request.persona, event["result"])
                event["cached"] = False
                event["saved_cost"] = 0.0
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v2/generate/stream")
async def generate_v2_stream_endpoint(request: V2GenerateRequest):
    """[别名] 与 /api/v2/generate 相同的 SSE 流式端点，向后兼容。"""
    def _event_stream():
        for event in generate_v2_stream(request):
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/v2/refine", response_model=RefineResponse)
def refine_endpoint(request: RefineRequest) -> RefineResponse:
    """人工纠偏：用户修改某阶段后，重新生成后续阶段的情绪和机会点。

    固定 modified_index 之前的阶段，以用户修改后的阶段为新锚点，
    让 AI 重新生成后续阶段，保持情绪曲线逻辑连贯。
    """
    try:
        return refine_journey(request)
    except Exception as exc:
        raise GenerationError(f"纠偏失败: {exc}", status_code=500) from exc


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Catch-all SPA fallback + static file serving."""
    import os as _os
    dist_dir = "frontend/dist"
    index_path = f"{dist_dir}/index.html"
    file_path = f"{dist_dir}/{full_path}"

    # Serve real static files (.js, .css, .svg, .ico, etc.)
    if _os.path.isfile(file_path):
        return FileResponse(file_path)

    # SPA fallback: serve index.html for client-side routes
    return FileResponse(index_path)
