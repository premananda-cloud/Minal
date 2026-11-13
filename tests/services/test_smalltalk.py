import pytest

from minal.services.smalltalk import is_small_talk


@pytest.mark.parametrize("q", ["hi", "Hello!", "hey", "Good morning", "thanks", "Thank you!",
                               "ok thanks", "bye", "who are you?", "What can you do?",
                               "namaste", "  hii  "])
def test_small_talk(q):
    assert is_small_talk(q)


@pytest.mark.parametrize("q", ["hi, who teaches CS201?", "thanks, what are the credits for CS101?",
                               "Who is Dr Rao?", "help me find a course", "", "???"])
def test_real_questions_are_not_small_talk(q):
    assert not is_small_talk(q)
