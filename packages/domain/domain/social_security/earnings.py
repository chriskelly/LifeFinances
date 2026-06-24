from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from core.social_security import AnnualEarnings

_NAMESPACE = {"osss": "http://ssa.gov/osss/schemas/2.0"}


def _required_text(element: ElementTree.Element, path: str, year: int) -> str:
    child = element.find(path, _NAMESPACE)
    if child is None or child.text is None:
        raise ValueError(f"missing {path} for SSA earnings year {year}")
    return child.text.strip()


def parse_social_security_statement_xml(xml_text: str) -> list[AnnualEarnings]:
    """Parse SSA statement XML into annual capped FICA earnings."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("invalid SSA statement XML") from exc

    record = root.find("osss:EarningsRecord", _NAMESPACE)
    if record is None:
        raise ValueError("SSA statement XML is missing EarningsRecord")

    earnings: list[AnnualEarnings] = []
    for row in record.findall("osss:Earnings", _NAMESPACE):
        start_year_raw = row.attrib.get("startYear")
        end_year_raw = row.attrib.get("endYear")
        if start_year_raw is None or end_year_raw is None:
            raise ValueError("SSA earnings row is missing startYear or endYear")
        start_year = int(start_year_raw)
        end_year = int(end_year_raw)
        if start_year != end_year:
            raise ValueError(f"SSA earnings row is multi-year: {start_year}-{end_year}")
        fica_text = _required_text(row, "osss:FicaEarnings", start_year)
        try:
            fica_earnings = Decimal(fica_text)
        except InvalidOperation as exc:
            raise ValueError(
                f"malformed FicaEarnings for SSA earnings year {start_year}"
            ) from exc
        if fica_earnings == Decimal("-1"):
            continue
        earnings.append(AnnualEarnings(year=start_year, fica_earnings=fica_earnings))
    return earnings
