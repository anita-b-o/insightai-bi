from types import SimpleNamespace

from app.services.openai_service import extract_text


def test_extract_text_prefers_output_text():
    response = SimpleNamespace(output_text="  final answer  ", output=[])

    assert extract_text(response) == "final answer"


def test_extract_text_falls_back_to_message_content():
    response = SimpleNamespace(
        output_text="",
        output=[
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(type="output_text", text="First line"),
                    SimpleNamespace(type="output_text", text="Second line"),
                ],
            )
        ],
    )

    assert extract_text(response) == "First line\nSecond line"


def test_extract_text_returns_none_without_usable_content():
    response = SimpleNamespace(output_text="", output=[SimpleNamespace(type="tool_call", content=[])])

    assert extract_text(response) is None
