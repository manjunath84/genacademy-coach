import genacademy_rag

import genacademy_coach


def test_imports_week2_foundation():
    assert genacademy_coach.__doc__
    assert genacademy_rag.__name__ == "genacademy_rag"
