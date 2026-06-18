import pytest

from genacademy_coach.privacy import (
    learner_input_hash,
    topic_hash,
    topic_hash_or_existing,
    user_id_hash,
)


def test_topic_and_input_hashes_are_stable_and_domain_separated():
    assert topic_hash(" agent   harness ") == topic_hash("agent harness")
    assert learner_input_hash(" agent   harness ") == learner_input_hash("agent harness")
    assert topic_hash("agent harness") != learner_input_hash("agent harness")


def test_user_id_hash_requires_salt_and_changes_by_salt():
    assert user_id_hash("learner@example.com", salt="salt-a") != user_id_hash(
        "learner@example.com",
        salt="salt-b",
    )
    with pytest.raises(ValueError, match="MEMORY_USER_SALT"):
        user_id_hash("learner@example.com", salt=" ")


def test_topic_hash_or_existing_keeps_existing_hashes():
    hashed = topic_hash("agent harness")

    assert topic_hash_or_existing(hashed) == hashed
    assert topic_hash_or_existing("agent harness") == hashed
