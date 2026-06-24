from langchain_core.messages import AIMessage

from genacademy_coach.teach_session import StaticAgentPort, _sum_usage
from genacademy_coach.teach_types import CoachAgentResponse, TokenUsage
from genacademy_coach.trace import load_trace


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


def test_trace_records_latency_and_threaded_tokens(make_session):
    session, trace_dir = make_session(
        last_usage=TokenUsage(input_tokens=11, output_tokens=7, total_tokens=18)
    )
    session.start()
    rows = load_trace(trace_dir / f"{session.session_id}.jsonl")
    assert rows[-1].input_tokens == 11 and rows[-1].total_tokens == 18
    assert rows[-1].latency_ms > 0.0
