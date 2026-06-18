from __future__ import annotations

import argparse
import uuid

from genacademy_coach.foundation import Foundation
from genacademy_coach.privacy import user_id_hash
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
    parser.add_argument("--user-id", default=None)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    hashed_user_id = (
        user_id_hash(args.user_id, salt=settings.memory_user_salt)
        if args.user_id and settings.memory_user_salt
        else None
    )
    session = CoachSession(
        session_id=args.session_id or uuid.uuid4().hex[:12],
        topic=args.topic,
        settings=settings,
        foundation=foundation,
        profile=LearnerProfile(style=args.style, track_lens=args.track_lens),
        user_id_hash=hashed_user_id,
    )
    first = session.start()
    print(first.response.learner_message)
    if first.response.check_question:
        print(f"\nCheck: {first.response.check_question}")
    if args.learner_answer:
        second = session.respond(args.learner_answer)
        print("\nAfter learner answer:")
        print(second.response.learner_message)
    session.finish()
    print(f"\ntrace={first.trace_path}")


if __name__ == "__main__":
    main()
