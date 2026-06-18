"""
LLM 客户端：封装 OpenAI 兼容接口调用，支持重试与 mock 回退。
"""

import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

PROMPT_ROOT = Path(__file__).resolve().parent.parent / "prompts"


def read_prompt(relative_path: str, variables: dict[str, str]) -> str:
    template = (PROMPT_ROOT / relative_path).read_text(encoding="utf-8")
    for key, value in variables.items():
        template = template.replace("{" + key + "}", value)
    return template


class LLMClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.timeout = int(os.getenv("LLM_TIMEOUT", "40"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.mock = os.getenv("LLM_MOCK", "1") != "0"

    def complete_json(self, prompt: str, retries: int = 1, step: str = "") -> dict[str, Any]:
        if self.mock or not self.api_key:
            return self._mock_response(step)

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return self._call_openai(prompt)
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1)
        raise RuntimeError(f"LLM 调用失败，已重试 {retries} 次：{last_error}")

    def _call_openai(self, prompt: str) -> dict[str, Any]:
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            timeout=self.timeout,
        )
        raw = response.choices[0].message.content or ""
        # 去除可能的 Markdown 代码块包裹
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)

    def _mock_response(self, step: str = "") -> dict[str, Any]:
        if step == "v2_step1":
            return self._mock_v2_step1()
        if step == "v2_step2":
            return self._mock_v2_step2()
        if step == "v2_step3":
            return self._mock_v2_step3()
        if step == "v2_step4":
            return self._mock_v2_step4()
        return self._mock_v1_response()

    def _mock_v1_response(self) -> dict[str, Any]:
        return {
            "stages": [
                {
                    "phase": "发现产品",
                    "behavior": "用户通过搜索引擎或社交媒体首次接触到产品，浏览首页了解产品核心价值",
                    "emotion_score": 7,
                    "pain_point": "首页信息密度高，用户难以快速判断产品是否匹配自身需求",
                    "opportunity": "在首屏提供一句话价值主张和 30 秒演示视频",
                },
                {
                    "phase": "了解功能",
                    "behavior": "用户深入浏览功能介绍页和案例展示，对比竞品评估产品能力",
                    "emotion_score": 6,
                    "pain_point": "功能描述偏技术化，缺少场景化表达导致理解门槛高",
                    "opportunity": "用用户场景故事重写功能描述，前置典型案例旅程",
                },
                {
                    "phase": "首次试用",
                    "behavior": "用户输入产品名称和用户画像，点击生成按钮等待首次产出",
                    "emotion_score": 5,
                    "pain_point": "首次输入格式不确定，担心输入不当导致生成结果无意义",
                    "opportunity": "提供示例输入快捷按钮和输入格式实时校验提示",
                },
                {
                    "phase": "等待生成",
                    "behavior": "用户观察生成进度，评估等待时间是否在可接受范围内",
                    "emotion_score": 4,
                    "pain_point": "等待时间不确定，缺少进度反馈引发焦虑感和放弃念头",
                    "opportunity": "展示分步进度条和预估剩余时间，允许后台生成并通知",
                },
                {
                    "phase": "查看结果",
                    "behavior": "用户仔细阅读生成的旅程地图、情绪曲线和流程图，评估质量和可用性",
                    "emotion_score": 8,
                    "pain_point": "信息量密集，首次查看容易在大量数据中迷失关注焦点",
                    "opportunity": "高亮关键情绪拐点并在顶部提供摘要面板快速概览",
                },
                {
                    "phase": "迭代优化",
                    "behavior": "用户调整输入参数或修改画像描述，对比多次生成结果以寻找最优版本",
                    "emotion_score": 6,
                    "pain_point": "缺少版本对比视图，难以判断迭代是否在向正确方向改善",
                    "opportunity": "提供历史记录面板和并排对比功能，支持标记最佳版本",
                },
                {
                    "phase": "导出复用",
                    "behavior": "用户复制 Mermaid 代码或导出完整 Markdown 报告，用于团队分享和文档归档",
                    "emotion_score": 8,
                    "pain_point": "导出的 Mermaid 代码在 Confluence 或 Notion 等平台可能渲染异常",
                    "opportunity": "预览渲染效果并标记已知平台兼容性问题，提供替代方案",
                },
            ],
            "summary": "用户整体旅程呈现典型的SaaS产品探索曲线：从好奇探索（7分）到经历等待焦虑的谷底（4分），最后在获得价值后情绪回升（8分）。",
        }

    def _mock_v2_step1(self) -> dict[str, Any]:
        return {
            "stages": [
                {"phase": "发现产品"},
                {"phase": "注册账号"},
                {"phase": "首次使用"},
                {"phase": "等待生成"},
                {"phase": "查看结果"},
                {"phase": "迭代优化"},
                {"phase": "导出复用"},
            ]
        }

    def _mock_v2_step2(self) -> dict[str, Any]:
        return {
            "stages": [
                {
                    "phase": "发现产品",
                    "behavior": "用户通过搜索引擎或社交媒体接触到产品，浏览首页了解核心价值主张",
                    "pain_point": "首页信息密度高，难以在 5 秒内判断产品是否匹配自身需求",
                },
                {
                    "phase": "注册账号",
                    "behavior": "用户填写邮箱和密码完成注册，阅读服务条款后点击同意",
                    "pain_point": "注册流程有 3 个步骤，每多一步就多一层流失风险",
                },
                {
                    "phase": "首次使用",
                    "behavior": "用户输入产品名称和用户画像，点击生成按钮等待首次产出",
                    "pain_point": "不确定输入格式要求，担心输入错误导致无效结果",
                },
                {
                    "phase": "等待生成",
                    "behavior": "用户观察生成进度指示器，估计剩余等待时间，可能切换标签页",
                    "pain_point": "等待时间不确定且没有中途反馈，焦虑感线性上升",
                },
                {
                    "phase": "查看结果",
                    "behavior": "用户仔细阅读旅程地图各阶段卡片、情绪曲线和流程图",
                    "pain_point": "信息量大而密集，首次查看容易在细节中迷失整体脉络",
                },
                {
                    "phase": "迭代优化",
                    "behavior": "用户调整输入参数或修改用户画像描述，重新生成以对比质量",
                    "pain_point": "缺少版本并排对比功能，难以判断迭代方向是否正确",
                },
                {
                    "phase": "导出复用",
                    "behavior": "用户复制图表代码或导出完整 Markdown 报告用于团队分享",
                    "pain_point": "导出的 Mermaid 代码在部分知识库平台渲染异常",
                },
            ]
        }

    def _mock_v2_step3(self) -> dict[str, Any]:
        return {
            "stages": [
                {
                    "phase": "发现产品",
                    "emotion_score": 7,
                    "emotion_rationale": "对新工具的期待感使情绪起点偏高，但不确定能否满足需求",
                    "opportunity": "在首屏用一句话价值主张 + 动画演示快速建立信任",
                },
                {
                    "phase": "注册账号",
                    "emotion_score": 5,
                    "emotion_rationale": "注册步骤打断探索心流，填写信息带来轻微烦躁",
                    "opportunity": "支持第三方快捷登录（Google/GitHub），减少输入负担",
                },
                {
                    "phase": "首次使用",
                    "emotion_score": 6,
                    "emotion_rationale": "首次输入有探索新鲜感但伴随不确定性，略高于注册阶段",
                    "opportunity": "提供示例输入按钮和智能占位符，降低首次使用门槛",
                },
                {
                    "phase": "等待生成",
                    "emotion_score": 5,
                    "emotion_rationale": "等待焦虑使情绪下滑，不确定结果质量加重了不安",
                    "opportunity": "展示分步进度条和预估剩余时间，允许后台生成并通知",
                },
                {
                    "phase": "查看结果",
                    "emotion_score": 8,
                    "emotion_rationale": "获得结构化结果带来满足感，情绪显著回升形成波峰",
                    "opportunity": "高亮情绪拐点并在顶部提供摘要面板，帮助快速定位重点",
                },
                {
                    "phase": "迭代优化",
                    "emotion_score": 6,
                    "emotion_rationale": "对比需求未满足导致情绪略回落，但仍有探索动力",
                    "opportunity": "提供历史版本并排对比和差异高亮，让迭代方向可视化",
                },
                {
                    "phase": "导出复用",
                    "emotion_score": 8,
                    "emotion_rationale": "产出可交付物带来成就感，分享预期使情绪保持高位",
                    "opportunity": "预览各平台渲染效果并给出兼容性提示，一键复制适配版本",
                },
            ]
        }

    def _mock_v2_step4(self) -> dict[str, Any]:
        return {
            "stages": [
                {
                    "phase": "发现产品",
                    "behavior": "用户通过搜索引擎或社交媒体接触到产品，浏览首页了解核心价值主张",
                    "emotion_score": 7,
                    "pain_point": "首页信息密度高，难以在 5 秒内判断产品是否匹配自身需求",
                    "opportunity": "在首屏用一句话价值主张 + 动画演示快速建立信任",
                },
                {
                    "phase": "注册账号",
                    "behavior": "用户填写邮箱和密码完成注册，阅读服务条款后点击同意",
                    "emotion_score": 5,
                    "pain_point": "注册流程有 3 个步骤，每多一步就多一层流失风险",
                    "opportunity": "支持第三方快捷登录（Google/GitHub），减少输入负担",
                },
                {
                    "phase": "首次使用",
                    "behavior": "用户输入产品名称和用户画像，点击生成按钮等待首次产出",
                    "emotion_score": 6,
                    "pain_point": "不确定输入格式要求，担心输入错误导致无效结果",
                    "opportunity": "提供示例输入按钮和智能占位符，降低首次使用门槛",
                },
                {
                    "phase": "等待生成",
                    "behavior": "用户观察生成进度指示器，估计剩余等待时间，可能切换标签页",
                    "emotion_score": 5,
                    "pain_point": "等待时间不确定且没有中途反馈，焦虑感线性上升",
                    "opportunity": "展示分步进度条和预估剩余时间，允许后台生成并通知",
                },
                {
                    "phase": "查看结果",
                    "behavior": "用户仔细阅读旅程地图各阶段卡片、情绪曲线和流程图",
                    "emotion_score": 8,
                    "pain_point": "信息量大而密集，首次查看容易在细节中迷失整体脉络",
                    "opportunity": "高亮情绪拐点并在顶部提供摘要面板，帮助快速定位重点",
                },
                {
                    "phase": "迭代优化",
                    "behavior": "用户调整输入参数或修改用户画像描述，重新生成以对比质量",
                    "emotion_score": 6,
                    "pain_point": "缺少版本并排对比功能，难以判断迭代方向是否正确",
                    "opportunity": "提供历史版本并排对比和差异高亮，让迭代方向可视化",
                },
                {
                    "phase": "导出复用",
                    "behavior": "用户复制图表代码或导出完整 Markdown 报告用于团队分享",
                    "emotion_score": 8,
                    "pain_point": "导出的 Mermaid 代码在部分知识库平台渲染异常",
                    "opportunity": "预览各平台渲染效果并给出兼容性提示，一键复制适配版本",
                },
            ],
            "summary": "用户旅程呈现典型的探索-挫折-回升曲线：从发现产品的好奇（7分）经历注册摩擦（5分）和等待焦虑（4分谷底），在获得有价值结果后情绪强劲反弹（8分）。关键体验断点在注册环节的摩擦和等待阶段的不确定性，改善这两处将显著提升整体旅程满意度。",
            "mermaid_code": """xychart-beta
    title \"用户情绪旅程\"
    x-axis [\"发现产品\", \"注册账号\", \"首次使用\", \"等待生成\", \"查看结果\", \"迭代优化\", \"导出复用\"]
    y-axis \"情绪评分\" 0 --> 10
    line [7, 5, 6, 5, 8, 6, 8]""",
        }
