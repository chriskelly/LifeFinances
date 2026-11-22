import re


def details_open_tag(body: str, section_id: str) -> str:
    match = re.search(
        rf'<details class="editor-section" id="{re.escape(section_id)}"[^>]*>',
        body,
    )
    assert match, f"missing editor section {section_id}"
    return match.group(0)


def _has_open_attribute(tag: str) -> bool:
    return re.search(r"(?:^|\s)open(?=\s|>|=)", tag) is not None


def assert_section_open(body: str, section_id: str) -> None:
    assert _has_open_attribute(details_open_tag(body, section_id)), (
        f"{section_id} should be open"
    )


def assert_section_closed(body: str, section_id: str) -> None:
    assert not _has_open_attribute(details_open_tag(body, section_id)), (
        f"{section_id} should be closed"
    )
