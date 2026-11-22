import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    parent: Node | None = field(default=None, repr=False)
    children: list[Node] = field(default_factory=list)
    text: str = ""

    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def ancestors(self) -> Iterator[Node]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def descendants(self) -> Iterator[Node]:
        for child in self.children:
            yield child
            yield from child.descendants()


class _FragmentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self._stack = [self.root]
        self._template_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "template":
            self._template_depth += 1
            return
        if self._template_depth:
            return
        node = Node(tag, _attrs(attrs), parent=self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "template" or self._template_depth:
            return
        node = Node(tag, _attrs(attrs), parent=self._stack[-1])
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        if tag == "template":
            self._template_depth = max(0, self._template_depth - 1)
            return
        if self._template_depth:
            return
        while len(self._stack) > 1 and self._stack[-1].tag != tag:
            self._stack.pop()
        if len(self._stack) > 1:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._template_depth == 0:
            self._stack[-1].text += data


def parse_fragment(body: str) -> Node:
    parser = _FragmentParser()
    parser.feed(body)
    parser.close()
    return parser.root


def rendered_rows(body: str, row_class: str) -> list[Node]:
    return [
        node
        for node in parse_fragment(body).descendants()
        if node.tag == "details" and {"row", row_class}.issubset(node.classes())
    ]


def assert_row_collapsed(body: str, row_class: str) -> None:
    rows = rendered_rows(body, row_class)
    assert rows, f"missing {row_class} row"
    assert all("open" not in row.attrs for row in rows), (
        f"{row_class} rows should be collapsed"
    )


def row_summary_labels(body: str) -> list[str]:
    return [
        _node_text(node).strip()
        for node in parse_fragment(body).descendants()
        if node.tag == "span" and "data-summary-label" in node.attrs
    ]


def assert_sabbatical_rows_nested_in_job(body: str) -> None:
    containers = [
        node
        for node in parse_fragment(body).descendants()
        if node.tag == "div"
        and "rows" in node.classes()
        and node.attrs.get("data-prefix") == "sabbaticals"
    ]
    assert containers, "missing sabbaticals container"

    container = containers[0]
    ancestors = list(container.ancestors())
    job = next(
        (
            node
            for node in ancestors
            if node.tag == "details" and "job-row" in node.classes()
        ),
        None,
    )
    fields = next(
        (
            node
            for node in ancestors
            if node.tag == "div" and "row-fields" in node.classes()
        ),
        None,
    )

    assert job is not None, "sabbaticals container is not inside a job row"
    assert fields is not None, "sabbaticals container is not inside .row-fields"
    assert job in fields.ancestors(), "job row does not contain its .row-fields"


def template_contains_row(body: str, row_class: str) -> bool:
    return (
        re.search(
            rf'<template class="row-template">\s*<details class="row {re.escape(row_class)}"',
            body,
        )
        is not None
    )


def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {name: value or "" for name, value in attrs}


def _node_text(node: Node) -> str:
    return node.text + "".join(_node_text(child) for child in node.children)
