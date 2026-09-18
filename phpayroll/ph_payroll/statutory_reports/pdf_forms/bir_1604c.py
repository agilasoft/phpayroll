# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""BIR Form 1604-C January 2018 (ENCS): overlay fillable fields on the official PDF."""

from __future__ import annotations

import os

from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import (
	amount_in_cell,
	checkbox_field,
	comb_field,
	comb_in_cell,
	text_field,
	text_on_ticks,
)

MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
TAX_Y = (390.05, 403.49, 416.93, 430.37, 443.81, 457.39, 470.83, 484.27, 497.71, 511.15, 524.59, 538.03)
REMIT_Y = (594.07, 607.51, 620.96, 634.54, 647.98, 661.42, 674.86, 688.30, 701.74, 715.18, 728.62, 742.06)


def _pdf_dir():
	return os.path.normpath(
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "public", "pdf")
	)


def get_source_pdf_path():
	return os.path.join(_pdf_dir(), "bir_form_1604c_january_2018_encs.pdf")


def get_fillable_pdf_path():
	return os.path.join(_pdf_dir(), "bir_form_1604c_fillable.pdf")


def context_from_filters(filters):
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import get_1604c_context

	return get_1604c_context(filters)


def get_field_layout() -> list[dict]:
	fields: list[dict] = []
	fields.append(comb_in_cell("year", 135.14, 115.94, 4, slot_w=18.32, box_h=10.32, page=0))
	fields.append(checkbox_field("amended_yes", 306.24, 119.90, width=13.68, height=12.24, page=0))
	fields.append(checkbox_field("amended_no", 356.76, 120.50, width=13.68, height=12.12, page=0))
	fields.append(comb_in_cell("sheets_attached", 553.06, 115.94, 2, slot_w=19.20, box_h=10.32, page=0))

	fields.append(comb_in_cell("tin_1", 237.89, 156.74, 3, slot_w=13.97, box_h=11.52, page=0))
	fields.append(comb_in_cell("tin_2", 293.81, 156.74, 3, slot_w=14.02, box_h=11.52, page=0))
	fields.append(comb_in_cell("tin_3", 349.87, 156.74, 3, slot_w=14.24, box_h=11.52, page=0))
	fields.append(comb_in_cell("tin_4", 406.99, 156.74, 5, slot_w=13.88, box_h=11.52, page=0))
	fields.append(comb_in_cell("rdo_code", 546.70, 156.74, 3, slot_w=14.92, box_h=11.52, page=0))
	fields.append(text_on_ticks("taxpayer_name", 27.84, 195.90, 558.0, page=0))
	fields.append(text_on_ticks("registered_address", 27.84, 227.90, 430.0, page=0))
	fields.append(comb_field("zip_code", 531.82, 241.00, 4, slot_w=14.88, height=12.0, page=0))
	fields.append(checkbox_field("category_private", 177.48, 258.70, width=13.44, height=11.52, page=0))
	fields.append(checkbox_field("category_government", 240.48, 259.10, width=13.32, height=11.52, page=0))
	fields.append(checkbox_field("top_wa_yes", 492.96, 258.80, width=13.44, height=11.40, page=0))
	fields.append(checkbox_field("top_wa_no", 542.76, 258.80, width=13.44, height=11.52, page=0))
	fields.append(text_field("contact_number", 108.00, 279.70, 70.0, 12.0, page=0))
	fields.append(text_field("email", 268.00, 279.70, 318.0, 12.0, page=0))
	fields.append(checkbox_field("refund_yes", 210.41, 318.89, width=13.80, height=12.00, page=0))
	fields.append(checkbox_field("refund_no", 265.85, 318.89, width=13.92, height=12.00, page=0))

	for name, y in zip(MONTHS, TAX_Y):
		fields.append(amount_in_cell(f"tax_{name}", 480.46, y, 106.56, box_h=9.24, page=0))
	fields.append(amount_in_cell("tax_total", 480.46, 551.47, 106.56, box_h=9.24, page=0))
	for name, y in zip(MONTHS, REMIT_Y):
		fields.append(amount_in_cell(f"remit_{name}", 432.67, y, 154.10, box_h=9.24, page=0))
	fields.append(amount_in_cell("remit_total", 432.67, 755.50, 154.10, box_h=9.24, page=0))

	fields.append(text_field("signatory_name", 314.69, 853.50, 272.0, 12.0, page=0))
	fields.append(text_field("signatory_title", 314.69, 862.50, 272.0, 12.0, page=0))
	return fields


def values_from_context(ctx: dict) -> dict[str, str]:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import (
		checkbox,
		digits_only,
		format_amount,
		split_tin,
	)

	values: dict[str, str] = {}
	year = int(ctx.get("year") or 0)
	tin_1, tin_2, tin_3, tin_4 = split_tin(ctx.get("tin"), ctx.get("tin_branch"))
	monthly = ctx.get("monthly_tax") or {}
	values["year"] = f"{year:04d}" if year else ""
	values["amended_no"] = checkbox(True)
	values["sheets_attached"] = f"{int(ctx.get('sheets_attached') or 1):02d}"[-2:]
	values["tin_1"] = tin_1
	values["tin_2"] = tin_2
	values["tin_3"] = tin_3
	values["tin_4"] = tin_4
	values["rdo_code"] = digits_only(ctx.get("rdo_code"), 3)
	values["taxpayer_name"] = (ctx.get("registered_name") or "").upper()
	values["registered_address"] = (ctx.get("registered_address") or "").upper()
	values["zip_code"] = digits_only(ctx.get("zip"), 4)
	values["contact_number"] = digits_only(ctx.get("contact_number"))
	values["email"] = (ctx.get("email") or "").lower()
	values["category_private"] = checkbox(True)
	values["top_wa_no"] = checkbox(True)
	values["refund_no"] = checkbox(True)
	values["signatory_name"] = (ctx.get("signatory_name") or "").upper()
	values["signatory_title"] = (ctx.get("signatory_title") or "").upper()
	total = 0.0
	for index, name in enumerate(MONTHS, start=1):
		amount = float(monthly.get(index) or 0)
		if amount:
			values[f"tax_{name}"] = format_amount(amount)
			values[f"remit_{name}"] = format_amount(amount)
		total += amount
	values["tax_total"] = format_amount(total)
	values["remit_total"] = format_amount(total)
	return values


def write_fillable_pdf(source_path: str | None = None, dest_path: str | None = None) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import write_fillable_pdf as convert_pdf

	return convert_pdf(
		source_path or get_source_pdf_path(),
		dest_path or get_fillable_pdf_path(),
		get_field_layout(),
	)
