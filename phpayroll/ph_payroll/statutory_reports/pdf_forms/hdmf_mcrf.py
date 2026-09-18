# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Pag-IBIG HQP-PFF-053 Membership Savings Remittance Form (MSRF / MCRF) V03."""

from __future__ import annotations

import os

from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import (
	listing_text,
	repeat_data_pages,
	text_field,
	text_in_cell,
)

# Official HQP-PFF-053 V03 grid (letter, 72 dpi). Vertical rules:
# MID 22.3–67.3, Account 67.3–112.3, Program 112.3–166.3, Names 166.3–360.6,
# Period 360.6–401.7, Compensation 401.7–463.4, EE 463.4–493.1, ER 493.1–520.5,
# Total 520.5–552.6, Remarks 552.6–589.4.
ROWS_PER_PAGE = 28
ROW_Y = (
	251.3,
	264.6,
	277.6,
	290.8,
	303.9,
	317.1,
	330.3,
	343.4,
	356.6,
	371.8,
	385.0,
	398.1,
	411.3,
	424.5,
	437.6,
	450.8,
	463.9,
	477.1,
	490.2,
	503.4,
	516.6,
	529.6,
	542.9,
	555.9,
	569.1,
	582.2,
	595.4,
	608.6,
)


def _pdf_dir():
	return os.path.normpath(
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "public", "pdf")
	)


def get_source_pdf_path():
	return os.path.join(_pdf_dir(), "hdmf_form_mcrf_pff053_v03.pdf")


def get_fillable_pdf_path():
	return os.path.join(_pdf_dir(), "hdmf_form_mcrf_fillable.pdf")


def context_from_filters(filters):
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import get_agency_listing_context

	return get_agency_listing_context(filters)


def _col(name, x, right, y, page, font_size=6, align="left"):
	return listing_text(name, x, y, right - x, page=page, font_size=font_size, align=align)


def _header(page: int) -> list[dict]:
	pre = f"p{page}_"
	return [
		# Grey header "Pag-IBIG EMPLOYER'S ID NUMBER" is y 44.16–58.32; value cell is 58.32–87.02.
		text_in_cell(f"{pre}employer_id", 428.0, 58.32, 154.0, box_h=28.70, page=page),
		# Name writing band sits under the "EMPLOYER/BUSINESS NAME" label (ends y≈117.3).
		text_in_cell(f"{pre}employer_name", 28.0, 117.4, 555.0, box_h=17.20, page=page),
		# Locality writing band under Municipality/City … Province; ZIP has its own slot.
		text_in_cell(f"{pre}address", 188.0, 184.0, 308.0, box_h=20.50, page=page),
		text_in_cell(f"{pre}zip", 502.0, 184.0, 80.0, box_h=20.50, page=page),
		# Page/grand totals sit in the padding to the right of the printed ₱ glyphs.
		_col(f"{pre}page_ee", 472.8, 492.2, 623.8, page, font_size=5, align="right"),
		_col(f"{pre}page_er", 502.2, 519.6, 623.8, page, font_size=5, align="right"),
		_col(f"{pre}page_total", 529.8, 551.6, 623.8, page, font_size=5, align="right"),
		_col(f"{pre}grand_ee", 472.8, 492.2, 637.8, page, font_size=5, align="right"),
		_col(f"{pre}grand_er", 501.8, 519.6, 637.8, page, font_size=5, align="right"),
		_col(f"{pre}grand_total", 529.3, 551.6, 637.8, page, font_size=5, align="right"),
		text_field(f"{pre}signatory_name", 28.0, 704.0, 220.0, 12.0, page=page),
		text_field(f"{pre}signatory_title", 300.0, 704.0, 140.0, 12.0, page=page),
	]


def _row(index: int, y: float, page: int) -> list[dict]:
	p = f"r{index:02d}"
	return [
		_col(f"{p}_mid", 23.8, 66.1, y, page),
		_col(f"{p}_program", 113.8, 165.1, y, page),
		_col(f"{p}_last", 168.0, 212.0, y, page),
		_col(f"{p}_first", 213.0, 258.0, y, page),
		_col(f"{p}_middle", 312.0, 359.4, y, page),
		_col(f"{p}_period", 362.0, 400.5, y, page),
		_col(f"{p}_comp", 403.2, 462.2, y, page, align="right"),
		_col(f"{p}_ee", 465.0, 492.0, y, page, align="right"),
		_col(f"{p}_er", 494.6, 519.4, y, page, align="right"),
		_col(f"{p}_total", 522.0, 551.4, y, page, align="right"),
	]


def get_field_layout(copies: int = 1) -> list[dict]:
	fields: list[dict] = []
	for page in range(max(1, copies)):
		fields.extend(_header(page))
		for local, y in enumerate(ROW_Y, start=1):
			fields.extend(_row(page * ROWS_PER_PAGE + local, y, page))
	return fields


def values_from_context(ctx: dict, copies: int = 1) -> dict[str, str]:
	from frappe.utils import flt

	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import digits_only, format_amount

	month = int(ctx.get("month") or 0)
	year = int(ctx.get("year") or 0)
	period = f"{month:02d}{year:04d}" if month and year else ""
	employees = list(ctx.get("employees") or [])
	pages = max(1, copies)
	address = (ctx.get("registered_address") or "").upper()
	zip_code = str(ctx.get("zip") or "").strip()
	if zip_code and address.endswith(zip_code):
		address = address[: -len(zip_code)].rstrip(" ,")
	common = {
		"employer_id": digits_only(ctx.get("pagibig_employer_id")),
		"employer_name": (ctx.get("registered_name") or "").upper(),
		"address": address,
		"zip": zip_code,
		"signatory_name": ctx.get("signatory_name") or "",
		"signatory_title": ctx.get("signatory_title") or "",
	}
	values: dict[str, str] = {}
	grand_ee = grand_er = 0.0
	for page in range(pages):
		pre = f"p{page}_"
		for key, val in common.items():
			values[f"{pre}{key}"] = val
		page_ee = page_er = 0.0
		chunk = employees[page * ROWS_PER_PAGE : (page + 1) * ROWS_PER_PAGE]
		for local, row in enumerate(chunk, start=1):
			index = page * ROWS_PER_PAGE + local
			p = f"r{index:02d}"
			ee = flt(row.get("hd_ee"))
			er = flt(row.get("hd_er"))
			page_ee += ee
			page_er += er
			values[f"{p}_mid"] = digits_only(row.get("hdmf_no"))
			values[f"{p}_program"] = "PAG-IBIG I"
			values[f"{p}_last"] = (row.get("last_name") or "").upper()
			values[f"{p}_first"] = (row.get("first_name") or "").upper()
			values[f"{p}_middle"] = (row.get("middle_name") or "").upper()
			values[f"{p}_period"] = period
			values[f"{p}_comp"] = format_amount(row.get("basic") or row.get("gross") or 0)
			values[f"{p}_ee"] = format_amount(ee)
			values[f"{p}_er"] = format_amount(er)
			values[f"{p}_total"] = format_amount(ee + er)
		grand_ee += page_ee
		grand_er += page_er
		values[f"{pre}page_ee"] = f"{page_ee:.2f}"
		values[f"{pre}page_er"] = f"{page_er:.2f}"
		values[f"{pre}page_total"] = f"{page_ee + page_er:.2f}"
	for page in range(pages):
		pre = f"p{page}_"
		values[f"{pre}grand_ee"] = f"{grand_ee:.2f}"
		values[f"{pre}grand_er"] = f"{grand_er:.2f}"
		values[f"{pre}grand_total"] = f"{grand_ee + grand_er:.2f}"
	return values


def write_fillable_pdf(source_path: str | None = None, dest_path: str | None = None, copies: int = 1) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import write_fillable_pdf as convert_pdf

	source = source_path or get_source_pdf_path()
	dest = dest_path or get_fillable_pdf_path()
	paged = dest + ".src.pdf"
	repeat_data_pages(source, paged, copies)
	return convert_pdf(paged, dest, get_field_layout(copies))
