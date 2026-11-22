import re


def details_open_tag(body: str, section_id: str) -> str:
    match = re.search(
        rf'<details class="editor-section" id="{re.escape(section_id)}"[^>]*>',
        body,
    )
    assert match, f"missing editor section {section_id}"
    return match.group(0)


def assert_section_open(body: str, section_id: str) -> None:
    assert re.search(r"\bopen\b", details_open_tag(body, section_id))


def assert_section_closed(body: str, section_id: str) -> None:
    assert not re.search(r"\bopen\b", details_open_tag(body, section_id))
