from langchain_core.messages import AIMessage

from genacademy_coach.teach_session import StaticAgentPort, _sum_usage
from genacademy_coach.teach_types import CoachAgentResponse, TokenUsage


def test_sum_usage_sums_messages():
    msgs = [
        AIMessage(
            content="a",
            usage_metadata={"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
        ),
        AIMessage(
            content="b",
            usage_metadata={"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
        ),
    ]
    u = _sum_usage(msgs)
    assert (u.input_tokens, u.output_tokens, u.total_tokens) == (5, 6, 11)


def test_static_port_reports_zero_usage():
    port = StaticAgentPort(
        CoachAgentResponse(
            learner_message="x",
            observation="o",
            next_action="advance",
            strategy="summary",
            citation_ids=[],
        )
    )
    assert isinstance(port.last_usage, TokenUsage) and port.last_usage.total_tokens == 0
