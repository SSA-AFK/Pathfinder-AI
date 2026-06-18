"""
测试用户旅程地图生成器 —— TDD 红灯阶段。

所有测试预期失败：app.main 模块尚不存在。
"""

import pytest
from fastapi.testclient import TestClient

# 此时 app.main 不存在，导入将触发 ImportError —— 红灯
from app.main import app

client = TestClient(app)


class TestV1ResponseStructure:
    """V1 单次生成输出的结构合法性。"""

    def test_v1_response_structure(self):
        """
        V1 输出必须包含 stages 数组，其中每个 stage 有：
        phase, behavior, emotion_score(1-10), pain_point, opportunity。
        """
        res = client.post(
            "/api/generate",
            json={"product": "测试产品", "persona": "测试用户", "mode": "v1"},
        )
        assert res.status_code == 200, f"期望 200，实际 {res.status_code}"
        body = res.json()
        v1 = body.get("v1")
        assert v1 is not None, "响应缺少 v1 字段"
        stages = v1.get("stages")
        assert isinstance(stages, list), "stages 必须是列表"
        assert len(stages) >= 1, "stages 至少包含 1 个阶段"

        required_fields = {"phase", "behavior", "emotion_score", "pain_point", "opportunity"}
        for i, stage in enumerate(stages):
            missing = required_fields - set(stage.keys())
            assert not missing, f"阶段 {i} 缺少字段: {missing}"
            score = stage["emotion_score"]
            assert isinstance(score, int), f"emotion_score 必须是 int，实际 {type(score)}"
            assert 1 <= score <= 10, f"emotion_score 超出 1-10: {score}"


class TestV2ChainIntermediate:
    """V2 链式生成中间产物验证。"""

    def test_v2_chain_intermediate(self):
        """
        V2 模式生成后，response.traces 包含 4 步中间产物，
        每一 trace.output 可被 json.loads 解析为 dict。
        """
        res = client.post(
            "/api/generate",
            json={"product": "测试产品", "persona": "测试用户", "mode": "v2"},
        )
        assert res.status_code == 200, f"期望 200，实际 {res.status_code}"
        body = res.json()
        traces = body.get("traces")
        assert isinstance(traces, list), "traces 必须是列表"
        assert len(traces) == 4, f"V2 应有 4 步中间产物，实际 {len(traces)} 步"

        import json

        for trace in traces:
            step = trace.get("step")
            name = trace.get("name")
            output = trace.get("output")
            assert isinstance(step, int), f"step 应为 int: {step}"
            assert isinstance(name, str), f"name 应为 str: {name}"
            assert isinstance(output, dict) or isinstance(output, str), (
                f"output 应为 dict 或 JSON str: {type(output)}"
            )
            if isinstance(output, str):
                parsed = json.loads(output)
                assert isinstance(parsed, dict), "trace output JSON 解析后应为 dict"


class TestEmotionCurveContinuity:
    """情绪分数连续性约束。"""

    def test_emotion_curve_continuity(self):
        """
        V2 输出的情绪分数序列，相邻差值不可超过 3，
        以防止不真实的情感剧烈跳跃。
        """
        res = client.post(
            "/api/generate",
            json={"product": "测试产品", "persona": "测试用户", "mode": "v2"},
        )
        assert res.status_code == 200
        body = res.json()
        v2 = body.get("v2")
        assert v2 is not None, "响应缺少 v2 字段"
        stages = v2.get("stages", [])
        assert len(stages) >= 2, "需要至少 2 个阶段才能检验连续性"

        scores = [s["emotion_score"] for s in stages]
        for i in range(len(scores) - 1):
            diff = abs(scores[i + 1] - scores[i])
            assert diff <= 3, (
                f"阶段 {i}({scores[i]}) → 阶段 {i+1}({scores[i+1]}) "
                f"差值 {diff} > 3，情绪跳跃不自然"
            )


class TestMermaidSyntax:
    """Mermaid 代码合法性检查。"""

    def test_mermaid_syntax(self):
        """
        输出中的 mermaid_code 必须包含合法的 Mermaid 关键字：
        'graph LR' 或 'xychart-beta'。
        """
        res = client.post(
            "/api/generate",
            json={"product": "测试产品", "persona": "测试用户", "mode": "v1"},
        )
        assert res.status_code == 200
        body = res.json()
        v1 = body.get("v1")
        assert v1 is not None, "响应缺少 v1 字段"
        mermaid_code = v1.get("mermaid_code", "")
        assert isinstance(mermaid_code, str), "mermaid_code 必须是字符串"
        assert len(mermaid_code) > 0, "mermaid_code 不能为空"

        valid_keywords = ["graph LR", "xychart-beta"]
        found = any(kw in mermaid_code for kw in valid_keywords)
        assert found, (
            f"mermaid_code 中未发现合法关键字 {valid_keywords}，"
            f"实际内容: {mermaid_code[:120]}..."
        )
