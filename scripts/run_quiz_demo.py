from __future__ import annotations

import argparse
import uuid

from genacademy_coach.foundation import Foundation
from genacademy_coach.quiz_session import QuizSession
from genacademy_coach.settings import CoachSettings

VALID_OPTION_IDS = frozenset({"A", "B", "C", "D"})


def parse_answers(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def validate_answer_count(answers: list[str] | None, question_count: int) -> None:
    if answers is not None and len(answers) != question_count:
        raise ValueError(f"expected {question_count} answers, received {len(answers)}")


def validate_answers(answers: list[str] | None, question_count: int) -> None:
    validate_answer_count(answers, question_count)
    if answers is None:
        return
    invalid = sorted(set(answers) - VALID_OPTION_IDS)
    if invalid:
        raise ValueError(
            "answers must use option IDs A, B, C, or D; "
            f"received: {', '.join(invalid)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--question-count", type=int, default=3)
    parser.add_argument("--answers")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()

    answers = parse_answers(args.answers)
    try:
        validate_answers(answers, args.question_count)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    session = QuizSession(
        session_id=args.session_id or uuid.uuid4().hex[:12],
        topic=args.topic,
        settings=settings,
        foundation=foundation,
        question_count=args.question_count,
    )
    try:
        result = session.run(answers)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if result.refusal_reason is not None:
        print(f"refused={result.refusal_reason}")
        print(f"trace={result.trace_path}")
        return

    for idx, question in enumerate(result.questions, start=1):
        print(f"\nQuestion {idx} [{question.citation_id}]")
        print(question.prompt)
        for option in question.options:
            print(f"{option.option_id}. {option.text}")

    if answers is not None:
        print(f"\nscore={result.score}/{len(result.questions)}")
        for grade in result.grades:
            status = "correct" if grade.correct else "incorrect"
            print(
                f"{grade.question_id}: {status} "
                f"(selected={grade.selected_option_id}, answer={grade.correct_option_id})"
            )
    print(f"\ntrace={result.trace_path}")


if __name__ == "__main__":
    main()
