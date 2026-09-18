# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""SSS Form R-3 (REV. 08-99) Contribution Collection List."""

from __future__ import annotations

import os

from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import (
	checkbox_field,
	listing_text,
	repeat_data_pages,
	text_field,
)

ROWS_PER_PAGE = 15
ROW_Y = (
	186.5,
	201.4,
	217.0,
	232.7,
	250.6,
	266.6,
	282.6,
	298.4,
	314.3,
	329.6,
	348.0,
	365.9,
	383.8,
	401.6,
	417.3,
)


def _pdf_dir():
	return os.path.normpath(
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "public", "pdf")
	)


def get_source_pdf_path():
	return os.path.join(_pdf_dir(), "sss_form_r3_rev_08_99.pdf")


def get_fillable_pdf_path():
	return os.path.join(_pdf_dir(), "sss_form_r3_fillable.pdf")


def context_from_filters(filters):
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import get_agency_listing_context

	return get_agency_listing_context(filters)


def _header(page: int) -> list[dict]:
	pre = f"p{page}_"
	return [
		text_field(f"{pre}employer_id", 48.0, 102.0, 140.0, 12.0, page=page),
		text_field(f"{pre}employer_name", 194.0, 102.0, 400.0, 12.0, page=page),
		text_field(f"{pre}quarter_mm", 698.0, 102.0, 24.0, 12.0, page=page),
		text_field(f"{pre}quarter_yyyy", 726.0, 102.0, 36.0, 12.0, page=page),
		text_field(f"{pre}tel", 48.0, 128.0, 140.0, 12.0, page=page),
		text_field(f"{pre}address", 194.0, 128.0, 400.0, 12.0, page=page),
		checkbox_field(f"{pre}type_regular", 612.0, 131.0, width=12.0, height=12.0, page=page),
		checkbox_field(f"{pre}type_household", 682.0, 131.0, width=12.0, height=12.0, page=page),
		listing_text(f"{pre}page_no", 700.0, 436.0, 28.0, page=page, font_size=8),
		listing_text(f"{pre}page_of", 700.0, 462.0, 28.0, page=page, font_size=8),
		text_field(f"{pre}signatory_name", 568.0, 470.0, 180.0, 12.0, page=page),
		text_field(f"{pre}signatory_title", 568.0, 492.0, 120.0, 12.0, page=page),
		listing_text(f"{pre}page_ss", 390.0, 434.0, 70.0, page=page, font_size=8, align="right"),
		listing_text(f"{pre}page_ec", 575.0, 434.0, 55.0, page=page, font_size=8, align="right"),
		listing_text(f"{pre}grand_ss", 96.0, 474.0, 70.0, page=page, font_size=8, align="right"),
		listing_text(f"{pre}grand_ec", 164.0, 474.0, 55.0, page=page, font_size=8, align="right"),
	]


def _row(index: int, y: float, page: int) -> list[dict]:
	p = f"r{index:02d}"
	return [
		listing_text(f"{p}_ss_no", 48.0, y, 105.0, page=page),
		listing_text(f"{p}_last", 158.0, y, 70.0, page=page),
		listing_text(f"{p}_first", 230.0, y, 100.0, page=page),
		listing_text(f"{p}_mi", 338.0, y, 36.0, page=page),
		listing_text(f"{p}_ss1", 382.0, y, 58.0, page=page, align="right"),
		listing_text(f"{p}_ss2", 444.0, y, 62.0, page=page, align="right"),
		listing_text(f"{p}_ss3", 510.0, y, 56.0, page=page, align="right"),
		listing_text(f"{p}_ec1", 570.0, y, 34.0, page=page, align="right"),
		listing_text(f"{p}_ec2", 606.0, y, 32.0, page=page, align="right"),
		listing_text(f"{p}_ec3", 640.0, y, 30.0, page=page, align="right"),
		listing_text(f"{p}_sep", 674.0, y, 80.0, page=page),
	]


def get_field_layout(copies: int = 1) -> list[dict]:
	fields: list[dict] = []
	for page in range(max(1, copies)):
		fields.extend(_header(page))
		for local, y in enumerate(ROW_Y, start=1):
			fields.extend(_row(page * ROWS_PER_PAGE + local, y, page))
	return fields


def values_from_context(ctx: dict, copies: int = 1) -> dict[str, str]:
	from frappe.utils import flt, getdate

	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import checkbox, digits_only, format_amount

	month = int(ctx.get("month") or 0)
	year = int(ctx.get("year") or 0)
	q_end_month = ((month - 1) // 3 + 1) * 3 if month else 0
	slot = ((month - 1) % 3) + 1 if month else 1
	employees = list(ctx.get("employees") or [])
	pages = max(1, copies)
	common = {
		"employer_id": digits_only(ctx.get("sss_employer_no")),
		"employer_name": (ctx.get("registered_name") or "").upper(),
		"address": (ctx.get("registered_address") or "").upper(),
		"tel": digits_only(ctx.get("contact_number")),
		"quarter_mm": f"{q_end_month:02d}" if q_end_month else "",
		"quarter_yyyy": f"{year:04d}" if year else "",
		"type_regular": checkbox(True),
		"signatory_name": ctx.get("signatory_name") or "",
		"signatory_title": ctx.get("signatory_title") or "",
		"page_of": str(pages),
	}
	values: dict[str, str] = {}
	grand_ss = 0.0
	grand_ec = 0.0
	for page in range(pages):
		pre = f"p{page}_"
		for key, val in common.items():
			values[f"{pre}{key}"] = val
		values[f"{pre}page_no"] = str(page + 1)
		page_ss = 0.0
		page_ec = 0.0
		chunk = employees[page * ROWS_PER_PAGE : (page + 1) * ROWS_PER_PAGE]
		for local, row in enumerate(chunk, start=1):
			index = page * ROWS_PER_PAGE + local
			p = f"r{index:02d}"
			ss = flt(row.get("ss_ee")) + flt(row.get("ss_er")) + flt(row.get("wisp_ee")) + flt(row.get("wisp_er"))
			ec = flt(row.get("ec_er"))
			page_ss += ss
			page_ec += ec
			values[f"{p}_ss_no"] = digits_only(row.get("sss_no"))
			values[f"{p}_last"] = (row.get("last_name") or "").upper()
			values[f"{p}_first"] = (row.get("first_name") or "").upper()
			middle = (row.get("middle_name") or "").strip()
			values[f"{p}_mi"] = middle[:1].upper()
			values[f"{p}_ss{slot}"] = format_amount(ss)
			values[f"{p}_ec{slot}"] = format_amount(ec)
			left = getdate(row.get("relieving_date")) if row.get("relieving_date") else None
			if left and left.month == month and left.year == year:
				values[f"{p}_sep"] = left.strftime("%m%d%Y")
		# Last filled page carries running grand totals as printed on the form.
		grand_ss += page_ss
		grand_ec += page_ec
		values[f"{pre}page_ss"] = format_amount(page_ss)
		values[f"{pre}page_ec"] = format_amount(page_ec)
	for page in range(pages):
		pre = f"p{page}_"
		values[f"{pre}grand_ss"] = format_amount(grand_ss)
		values[f"{pre}grand_ec"] = format_amount(grand_ec)
	return values


def write_fillable_pdf(source_path: str | None = None, dest_path: str | None = None, copies: int = 1) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import write_fillable_pdf as convert_pdf

	source = source_path or get_source_pdf_path()
	dest = dest_path or get_fillable_pdf_path()
	paged = dest + ".src.pdf"
	repeat_data_pages(source, paged, copies)
	return convert_pdf(paged, dest, get_field_layout(copies))
