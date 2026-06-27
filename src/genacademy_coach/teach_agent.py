from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from genacademy_coach.teach_tools import TeachRuntime, build_teach_tools
from genacademy_coach.teach_types import CoachAgentResponse

DEFAULT_NEBIUS_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507-fast"
MODEL_CALL_RUN_LIMIT = 8
TOOL_CALL_RUN_LIMIT = 12
PER_TOOL_CALL_RUN_LIMITS = {
    "retrieve_course_corpus": 2,
    "generate_check_item_for_span": 2,
    "escalate_to_mentor": 1,
}

SYSTEM_PROMPT = """You are GenAcademy Coach, an adaptive grounded course tutor.

Rules:
- Use retrieve_course_corpus before teaching any course concept.
- Teach only from retrieved citation text.
- Every learner-visible factual claim must be supported by a retrieved citation.
- Include retrieved citation IDs inline in learner-visible answers, formatted like
  [citation_id].
- Keep explanations short and close to the retrieved wording. Do not add examples unless
  the retrieved text includes those examples.
- If no retrieved citation supports the topic, call escalate_to_mentor and refuse.
- Do not answer from model priors.
- Generate or use one grounded check question before grading understanding.
- Call retrieve_course_corpus at most once per turn unless the first result has no citeable spans.
- Call generate_check_item_for_span at most once per turn unless the tool returns an explicit error.
- Call escalate_to_mentor at most once per turn, then return refuse_escalate immediately.
- When calling generate_check_item_for_span, pass a retrieved citation_id. The runtime will enforce
  the preferred check span in this order: slide, handout, then first citeable span.
- Treat tool-returned retrieval scores as the only evidence score. Do not return confidence.
- Choose next_action at runtime from: advance, re_explain_differently, drill, refuse_escalate, stop.
- When grade_understanding returns correct=false, choose re_explain_differently with a strategy that
  differs from the prior failed strategy.
- Choose a strategy that differs from the failed previous explanation when the learner stumbles.
- Explain the observation that drove the decision: retrieval result, learner answer grade, prior
  strategy, and profile state.
- Return structured output with learner_message, observation, next_action, strategy, citation_ids,
  and optional check_question.
"""


def build_langchain_model(foundation: Any) -> ChatOpenAI:
    settings = foundation.rag_settings
    model_name = settings.gen_model or DEFAULT_NEBIUS_MODEL
    return ChatOpenAI(
        model=model_name,
        temperature=0,
        max_tokens=700,
        timeout=60,
        max_retries=2,
        api_key=settings.gen_api_key or "not-needed",
        base_url=settings.gen_base_url,
    )


def build_coach_agent(runtime: TeachRuntime, *, model: Any | None = None):
    active_model = model or build_langchain_model(runtime.foundation)
    middleware: list[Any] = [
        ModelCallLimitMiddleware(
            run_limit=MODEL_CALL_RUN_LIMIT,
            exit_behavior="end",
        )
    ]
    middleware.extend(
        ToolCallLimitMiddleware(
            tool_name=tool_name,
            run_limit=run_limit,
        )
        for tool_name, run_limit in PER_TOOL_CALL_RUN_LIMITS.items()
    )
    middleware.append(ToolCallLimitMiddleware(run_limit=TOOL_CALL_RUN_LIMIT))
    return create_agent(
        model=active_model,
        tools=build_teach_tools(runtime),
        middleware=middleware,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(CoachAgentResponse),
    )
