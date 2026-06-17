from __future__ import annotations

import argparse
import uuid

from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings
from genacademy_coach.skillgap_session import SkillGapSession


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", default=None)
    parser.add_argument(
        "--source-session-id",
        action="append",
        required=True,
        help="existing teach or quiz session id to diagnose; repeat for multiple sessions",
    )
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    session = SkillGapSession(
        session_id=args.session_id or f"skillgap-{uuid.uuid4().hex[:8]}",
        source_session_ids=args.source_session_id,
        settings=settings,
        foundation=foundation,
    )
    result = session.run()

    print("Skill-Gap Diagnosis")
    if not result.items:
        print("No trace-backed gaps found for the supplied sessions.")
        print(f"trace={result.trace_path}")
        return

    for index, item in enumerate(result.items, start=1):
        print(
            f"{index}. {item.gap_id} "
            f"priority={item.priority_score} "
            f"evidence={item.evidence_score:.3f} {item.evidence_band} "
            f"action={item.next_action}"
        )
        if item.review_next:
            print(f"   {item.review_next}")
        if item.reason_code:
            print(f"   refused={item.reason_code}")
        if item.citation_ids:
            print(f"   citations={', '.join(item.citation_ids)}")

    print(f"trace={result.trace_path}")


if __name__ == "__main__":
    main()
