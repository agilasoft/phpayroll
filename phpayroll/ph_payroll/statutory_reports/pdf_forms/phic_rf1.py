# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""PhilHealth RF-1 (Revised February 2014) Employer’s Remittance Report."""

from __future__ import annotations

import os

from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import (
	checkbox_field,
	listing_text,
	repeat_data_pages,
	text_field,
)

ROWS_PER_PAGE = 10
ROW_Y = (
	232.0,
	251.9,
	271.7,
	291.6,
	311.4,
	331.3,
	351.1,
	370.9,
	390.8,
	410.6,
)


def _pdf_dir():
	return os.path.normpath(
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "public", "pdf")
	)


def get_source_pdf_path():
	return os.path.join(_pdf_dir(), "phic_form_rf1_february_2014.pdf")


def get_fillable_pdf_path():
	return os.path.join(_pdf_dir(), "phic_form_rf1_fillable.pdf")


def context_from_filters(filters):
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import get_agency_listing_context

	return get_agency_listing_context(filters)


def _header(page: int) -> list[dict]:
	pre = f"p{page}_"
	return [
		text_field(f"{pre}pen", 190.0, 96.0, 330.0, 12.0, page=page),
		text_field(f"{pre}tin", 190.0, 110.0, 330.0, 12.0, page=page),
		text_field(f"{pre}employer_name", 220.0, 128.0, 300.0, 12.0, page=page),
		text_field(f"{pre}address", 220.0, 141.0, 300.0, 12.0, page=page),
		text_field(f"{pre}tel", 155.0, 164.0, 160.0, 12.0, page=page),
		text_field(f"{pre}email", 400.0, 164.0, 130.0, 12.0, page=page),
		checkbox_field(f"{pre}type_private", 543.0, 145.0, width=12.0, height=12.0, page=page),
		checkbox_field(f"{pre}report_regular", 612.0, 145.0, width=12.0, height=12.0, page=page),
		text_field(f"{pre}period", 738.0, 146.0, 60.0, 12.0, page=page),
		listing_text(f"{pre}page_count", 55.0, 442.0, 40.0, page=page, font_size=8),
		listing_text(f"{pre}subtotal", 620.0, 434.0, 80.0, page=page, font_size=8, align="right"),
		listing_text(f"{pre}grand_total", 620.0, 468.0, 80.0, page=page, font_size=8, align="right"),
		text_field(f"{pre}signatory_name", 150.0, 516.0, 220.0, 12.0, page=page),
		text_field(f"{pre}signatory_title", 390.0, 516.0, 180.0, 12.0, page=page),
	]


def _row(index: int, y: float, page: int) -> list[dict]:
	p = f"r{index:02d}"
	return [
		listing_text(f"{p}_pin", 48.0, y, 150.0, page=page),
		listing_text(f"{p}_last", 200.0, y, 108.0, page=page),
		listing_text(f"{p}_first", 310.0, y, 70.0, page=page),
		listing_text(f"{p}_middle", 428.0, y, 80.0, page=page),
		listing_text(f"{p}_sex", 578.0, y, 24.0, page=page),
		listing_text(f"{p}_ps", 652.0, y, 32.0, page=page, align="right"),
		listing_text(f"{p}_es", 686.0, y, 32.0, page=page, align="right"),
		listing_text(f"{p}_status", 722.0, y, 70.0, page=page),
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

	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import checkbox, digits_only, format_amount, format_tin_display

	month = int(ctx.get("month") or 0)
	year = int(ctx.get("year") or 0)
	employees = list(ctx.get("employees") or [])
	pages = max(1, copies)
	common = {
		"pen": digits_only(ctx.get("philhealth_pen")),
		"tin": format_tin_display(ctx.get("tin"), ctx.get("tin_branch")),
		"employer_name": (ctx.get("registered_name") or "").upper(),
		"address": (ctx.get("registered_address") or "").upper(),
		"tel": digits_only(ctx.get("contact_number")),
		"email": ctx.get("email") or "",
		"type_private": checkbox(True),
		"report_regular": checkbox(True),
		"period": f"{month:02d}/{year:04d}" if month and year else "",
		"signatory_name": ctx.get("signatory_name") or "",
		"signatory_title": ctx.get("signatory_title") or "",
	}
	values: dict[str, str] = {}
	grand = 0.0
	for page in range(pages):
		pre = f"p{page}_"
		for key, val in common.items():
			values[f"{pre}{key}"] = val
		sub = 0.0
		chunk = employees[page * ROWS_PER_PAGE : (page + 1) * ROWS_PER_PAGE]
		for local, row in enumerate(chunk, start=1):
			index = page * ROWS_PER_PAGE + local
			p = f"r{index:02d}"
			ee = flt(row.get("ph_ee"))
			er = flt(row.get("ph_er"))
			sub += ee + er
			values[f"{p}_pin"] = digits_only(row.get("phic_no"))
			values[f"{p}_last"] = (row.get("last_name") or "").upper()
			values[f"{p}_first"] = (row.get("first_name") or "").upper()
			values[f"{p}_middle"] = (row.get("middle_name") or "").upper()
			values[f"{p}_ps"] = format_amount(ee)
			values[f"{p}_es"] = format_amount(er)
			joined = getdate(row.get("date_of_joining")) if row.get("date_of_joining") else None
			left = getdate(row.get("relieving_date")) if row.get("relieving_date") else None
			if left and left.month == month and left.year == year:
				values[f"{p}_status"] = f"S {left.strftime('%m-%d-%Y')}"
			elif joined and joined.month == month and joined.year == year:
				values[f"{p}_status"] = f"NH {joined.strftime('%m-%d-%Y')}"
		grand += sub
		values[f"{pre}subtotal"] = format_amount(sub)
		values[f"{pre}page_count"] = str(len(chunk))
	for page in range(pages):
		values[f"p{page}_grand_total"] = format_amount(grand)
	return values


def write_fillable_pdf(source_path: str | None = None, dest_path: str | None = None, copies: int = 1) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import write_fillable_pdf as convert_pdf

	source = source_path or get_source_pdf_path()
	dest = dest_path or get_fillable_pdf_path()
	paged = dest + ".src.pdf"
	repeat_data_pages(source, paged, copies)
	return convert_pdf(paged, dest, get_field_layout(copies))
