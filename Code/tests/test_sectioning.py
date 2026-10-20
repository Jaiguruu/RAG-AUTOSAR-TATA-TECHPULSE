from autosar_rag.sectioning import SECTION_HEADING_RE, section_segments


def test_numbered_sections_split_content_without_losing_text():
    text = (
        "Introductory paragraph.\n\n"
        "1 Introduction\nThe introductory section.\n\n"
        "1.1 Scope\nScope details.\n"
    )
    segments = list(section_segments(text))
    assert len(segments) == 3
    assert [segment[2] for segment in segments] == [None, "1 Introduction", "1.1 Scope"]
    assert "Introductory paragraph." in segments[0][1]
    assert "The introductory section." in segments[1][1]
    assert "Scope details." in segments[2][1]
    assert "".join(segment[1] for segment in segments) == text


def test_numbered_list_item_is_not_treated_as_section_heading():
    assert not SECTION_HEADING_RE.match("1. Send the request to the service")
    assert SECTION_HEADING_RE.match("1.2 Send the request to the service")
