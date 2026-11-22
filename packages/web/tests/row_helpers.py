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
    def __init__(self, *, skip_templates: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self._stack = [self.root]
        self._skip_templates = skip_templates
        self._template_depth = 0
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "template" and self._skip_templates:
            self._template_depth += 1
            return
        if self._template_depth:
            return
        node = Node(tag, _attrs(attrs), parent=self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "template" and self._skip_templates:
            return
        if self._template_depth:
            return
        node = Node(tag, _attrs(attrs), parent=self._stack[-1])
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        if tag == "template" and self._skip_templates:
            self._template_depth = max(0, self._template_depth - 1)
            return
        if self._template_depth:
            return
        if len(self._stack) == 1:
            self.errors.append(f"unexpected closing tag </{tag}>")
            return
        if self._stack[-1].tag != tag:
            self.errors.append(f"expected </{self._stack[-1].tag}>, got </{tag}>")
            while len(self._stack) > 1 and self._stack[-1].tag != tag:
                self._stack.pop()
            if len(self._stack) > 1:
                self._stack.pop()
            return
        self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._template_depth == 0:
            self._stack[-1].text += data

    def finish(self) -> None:
        if len(self._stack) > 1:
            self.errors.append(
                "unclosed tags: " + ", ".join(node.tag for node in self._stack[1:])
            )


def parse_fragment(body: str, *, skip_templates: bool = True) -> Node:
    parser = _FragmentParser(skip_templates=skip_templates)
    parser.feed(body)
    parser.close()
    parser.finish()
    assert not parser.errors, f"malformed HTML: {parser.errors[:3]}"
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


def input_attrs(body: str, name: str) -> dict[str, str]:
    for node in parse_fragment(body).descendants():
        if node.tag == "input" and node.attrs.get("name") == name:
            return node.attrs
    raise AssertionError(f"missing input {name}")


def assert_row_templates(
    body: str, *, prefix: str, row_class: str, empty_label: str | None
) -> None:
    root = parse_fragment(body, skip_templates=False)
    containers = _rows_containers(root, prefix)
    assert containers, f"missing rows container for {prefix}"

    for container in containers:
        templates = [
            child
            for child in container.children
            if child.tag == "template" and "row-template" in child.classes()
        ]
        assert len(templates) == 1, f"{prefix} should have exactly one row template"

        row = _template_row(templates[0])
        assert row_class in row.classes(), f"{prefix} template should be {row_class}"
        assert row.attrs.get("data-empty-label") == empty_label, (
            f"{prefix} template fallback should be {empty_label!r}"
        )


def assert_sabbatical_rows_nested_in_job(body: str) -> None:
    rows = rendered_rows(body, "sabbatical-row")
    assert rows, "missing sabbatical rows"

    for row in rows:
        ancestors = list(row.ancestors())
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
        container = next(
            (
                node
                for node in ancestors
                if node.tag == "div"
                and "rows" in node.classes()
                and node.attrs.get("data-prefix") == "sabbaticals"
            ),
            None,
        )

        assert job is not None, "sabbatical row is not inside a job row"
        assert fields is not None, "sabbatical row is not inside .row-fields"
        assert container is not None, (
            "sabbatical row is not inside a sabbaticals container"
        )
        assert job in fields.ancestors(), "job row does not contain its .row-fields"
        assert fields in container.ancestors(), (
            "sabbaticals container is not inside .row-fields"
        )


def _rows_containers(root: Node, prefix: str) -> list[Node]:
    return [
        node
        for node in root.descendants()
        if node.tag == "div"
        and "rows" in node.classes()
        and node.attrs.get("data-prefix") == prefix
    ]


def _template_row(template: Node) -> Node:
    row = next(
        (
            child
            for child in template.children
            if child.tag == "details" and "row" in child.classes()
        ),
        None,
    )
    assert row is not None, "row template does not contain a details row"
    return row


def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {name: value or "" for name, value in attrs}


def _node_text(node: Node) -> str:
    return node.text + "".join(_node_text(child) for child in node.children)
