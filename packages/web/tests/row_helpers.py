import re


def row_details_tags(body: str, row_class: str) -> list[str]:
    return re.findall(rf'<details class="row {re.escape(row_class)}"[^>]*>', body)


def row_details_tag(body: str, row_class: str) -> str:
    tags = row_details_tags(body, row_class)
    assert tags, f"missing {row_class} row"
    return tags[0]


def assert_row_collapsed(body: str, row_class: str) -> None:
    tags = row_details_tags(body, row_class)
    assert tags, f"missing {row_class} row"
    assert all(" open" not in tag for tag in tags), (
        f"{row_class} rows should be collapsed"
    )


def row_summary_labels(body: str) -> list[str]:
    return re.findall(r"data-summary-label[^>]*>([^<]*)</span>", body)
