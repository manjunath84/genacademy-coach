from __future__ import annotations

import argparse
import uuid

from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument(
        "--style",
        default="analogy",
        choices=["concise", "analogy", "step_by_step"],
    )
    parser.add_argument(
        "--track-lens",
        default="code_heavy",
        choices=["low_code_no_code", "code_heavy", "bridge"],
    )
    parser.add_argument("--learner-answer")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    session = CoachSession(
        session_id=args.session_id or uuid.uuid4().hex[:12],
        topic=args.topic,
        settings=settings,
        foundation=foundation,
        profile=LearnerProfile(style=args.style, track_lens=args.track_lens),
    )
    first = session.start()
    print(first.response.learner_message)
    if first.response.check_question:
        print(f"\nCheck: {first.response.check_question}")
    if args.learner_answer:
        second = session.respond(args.learner_answer)
        print("\nAfter learner answer:")
        print(second.response.learner_message)
    print(f"\ntrace={first.trace_path}")


if __name__ == "__main__":
    main()
