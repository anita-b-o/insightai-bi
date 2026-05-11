from app.services.ai_service import parse_ai_answer_text


def test_parse_ai_answer_text_keeps_plain_answer():
    parsed = parse_ai_answer_text("La categoria mas vulnerable es bosques.")

    assert parsed == {
        "answer": "La categoria mas vulnerable es bosques.",
        "chart_suggestion": None,
    }


def test_parse_ai_answer_text_extracts_raw_json():
    parsed = parse_ai_answer_text('{"answer":"Bosques es la categoria mas vulnerable.","chart_suggestion":"bar_chart"}')

    assert parsed == {
        "answer": "Bosques es la categoria mas vulnerable.",
        "chart_suggestion": "bar",
    }


def test_parse_ai_answer_text_extracts_fenced_json():
    parsed = parse_ai_answer_text(
        '```json\n{"answer":"Bosques es la categoria mas vulnerable.","chart_suggestion":"line_chart"}\n```'
    )

    assert parsed == {
        "answer": "Bosques es la categoria mas vulnerable.",
        "chart_suggestion": "line",
    }


def test_parse_ai_answer_text_extracts_generic_fenced_json():
    parsed = parse_ai_answer_text(
        '```\n{"answer":"Bosques es la categoria mas vulnerable.","chart_suggestion":"pie_chart"}\n```'
    )

    assert parsed == {
        "answer": "Bosques es la categoria mas vulnerable.",
        "chart_suggestion": "pie",
    }


def test_parse_ai_answer_text_falls_back_on_malformed_json():
    text = '```json\n{"answer":"Bosques",\n```'

    parsed = parse_ai_answer_text(text)

    assert parsed == {
        "answer": '{"answer":"Bosques",',
        "chart_suggestion": None,
    }


def test_parse_ai_answer_text_normalizes_table_and_visualization_key():
    parsed = parse_ai_answer_text(
        '{"answer":"No matching rows were found.","visualization_suggestion":"table_chart"}'
    )

    assert parsed == {
        "answer": "No matching rows were found.",
        "chart_suggestion": "table",
    }
