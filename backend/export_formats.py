"""Serializers that turn a stored `canonical_data` dict into a downloadable
export (CSV / XLSX / JSON).

These read the JSON dict straight out of `Extraction.canonical_data` — no
Pydantic re-hydration — because the column is already the canonical shape
emitted by `CanonicalInvoice.model_dump(mode="json")`. In that shape money
amounts and quantities are precision-preserving *strings* ("1850.00") and
dates are ISO strings ("2026-05-12").

CSV and XLSX share one flattened layout: one row per line item, with the
document/seller/buyer fields repeated as leading columns. JSON is the full
nested structure, untouched.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

# UTF-8 BOM. Excel on Windows needs it to auto-detect UTF-8, otherwise
# Mkhedruli text in a CSV renders as mojibake.
_BOM = "﻿"

COLUMNS: list[str] = [
    "document_number",
    "document_date",
    "seller_name",
    "seller_tin",
    "buyer_name",
    "buyer_tin",
    "description",
    "quantity",
    "unit",
    "unit_price",
    "line_total",
    "currency",
]


def _num(value: Any) -> Any:
    """Coerce a numeric string to float so spreadsheets treat it as a number.

    Falls back to the original value when it isn't parseable (keeps the cell
    honest rather than zeroing it). None → "" for a blank cell.
    """
    if value is None:
        return ""
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _money_amount(money: dict[str, Any] | None) -> Any:
    return _num(money.get("amount")) if money else ""


def flatten_rows(canonical: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    """Return (header, rows). One row per line item; a document with no items
    still yields exactly one row (doc-level fields filled, item columns blank)."""
    seller = canonical.get("seller") or {}
    buyer = canonical.get("buyer") or {}
    doc_currency = canonical.get("document_currency") or ""

    lead = [
        canonical.get("document_number") or "",
        canonical.get("document_date") or "",
        seller.get("name") or "",
        seller.get("tin") or "",
        buyer.get("name") or "",
        buyer.get("tin") or "",
    ]

    items = canonical.get("items") or []
    rows: list[list[Any]] = []
    if not items:
        rows.append([*lead, "", "", "", "", "", doc_currency])
        return COLUMNS, rows

    for item in items:
        total = item.get("total") or {}
        rows.append(
            [
                *lead,
                item.get("description") or "",
                _num(item.get("quantity")),
                item.get("unit") or "",
                _money_amount(item.get("unit_price")),
                _money_amount(total),
                total.get("currency") or doc_currency,
            ]
        )
    return COLUMNS, rows


def to_csv(canonical: dict[str, Any]) -> bytes:
    header, rows = flatten_rows(canonical)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return (_BOM + buf.getvalue()).encode("utf-8")


def to_xlsx(canonical: dict[str, Any]) -> bytes:
    from openpyxl import Workbook

    header, rows = flatten_rows(canonical)
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoice"
    ws.append(header)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_json(canonical: dict[str, Any]) -> bytes:
    # Full nested canonical, Georgian kept literal (not \uXXXX-escaped).
    return json.dumps(canonical, indent=2, ensure_ascii=False).encode("utf-8")
