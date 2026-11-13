import pytest

from minal.llm import (
    LLM,
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    FakeLLM,
    LLMUnavailable,
)


def req(text="hi"):
    return CompletionRequest(messages=[ChatMessage(role="system", content="SYS"),
                                       ChatMessage(role="user", content=text)])


def test_single_string_repeats_and_records_calls():
    fake = FakeLLM("Hello")
    assert fake.complete(req("a")).text == "Hello"
    assert fake.complete(req("b")).text == "Hello"
    assert len(fake.calls) == 2 and fake.last.messages[-1].content == "b"


def test_sequence_is_consumed_in_order_then_errors():
    fake = FakeLLM(["one", "two"])
    assert [fake.complete(req()).text for _ in range(2)] == ["one", "two"]
    with pytest.raises(AssertionError):
        fake.complete(req())


def test_scripted_exception_is_raised_and_call_still_recorded():
    fake = FakeLLM([LLMUnavailable("down"), "back"])
    with pytest.raises(LLMUnavailable):
        fake.complete(req())
    assert fake.complete(req()).text == "back" and len(fake.calls) == 2


def test_scripted_result_is_passed_through():
    custom = CompletionResult(text="x", model="m", finish_reason="length")
    assert FakeLLM([custom]).complete(req()) is custom


def test_last_prompt_text_joins_all_messages():
    fake = FakeLLM()
    fake.complete(req("what is CS101?"))
    assert "SYS" in fake.last_prompt_text() and "CS101" in fake.last_prompt_text()


def test_fake_satisfies_the_port():
    llm: LLM = FakeLLM()
    assert llm.complete(req()).text == "OK"
