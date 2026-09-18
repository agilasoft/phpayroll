# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""BIR Form 1601-C January 2018 (ENCS): overlay fillable fields on the official PDF."""

from __future__ import annotations

import os

from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import (
	amount_in_cell,
	checkbox_field,
	comb_field,
	comb_in_cell,
	digit_cell,
	text_field,
	text_on_ticks,
)

# Right-hand money cells: left of the printed cents separator at x≈549.5.
AMOUNT_X = 391.0
AMOUNT_W = 157.5
# Top of each printed amount/cents band (item 14 is the first computation row).
ITEM_Y = {
	14: 293.93,
	15: 319.61,
	16: 335.57,
	17: 351.49,
	18: 367.45,
	19: 383.41,
	20: 399.33,
	21: 415.21,
	22: 431.17,
	23: 447.17,
	24: 463.13,
	25: 479.09,
	26: 495.05,
	27: 511.01,
	28: 526.97,
	29: 542.93,
	30: 558.89,
	31: 575.45,
	32: 591.41,
	33: 607.37,
	34: 623.37,
	35: 639.21,
	36: 655.17,
}


def _pdf_dir():
	return os.path.normpath(
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "public", "pdf")
	)


def get_source_pdf_path():
	return os.path.join(_pdf_dir(), "bir_form_1601c_january_2018_encs.pdf")


def get_fillable_pdf_path():
	return os.path.join(_pdf_dir(), "bir_form_1601c_fillable.pdf")


def context_from_filters(filters):
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import get_1601c_context

	return get_1601c_context(filters)


def get_field_layout() -> list[dict]:
	fields: list[dict] = []
	# Item 1: grey chrome ~18–46, white MM ~46–75, white YYYY ~75–132.
	fields.append(digit_cell("month_1", 46.20, 108.50, box_w=14.40, box_h=10.32, page=0))
	fields.append(digit_cell("month_2", 60.60, 108.50, box_w=14.18, box_h=10.32, page=0))
	for index, (x, w) in enumerate(
		((74.78, 14.40), (89.18, 14.28), (103.46, 14.40), (117.86, 14.16)), start=1
	):
		fields.append(digit_cell(f"year_{index}", x, 108.50, box_w=w, box_h=10.32, page=0))
	fields.append(checkbox_field("amended_yes", 183.60, 112.20, width=13.44, height=12.12, page=0))
	fields.append(checkbox_field("amended_no", 231.48, 112.32, width=13.32, height=12.24, page=0))
	fields.append(checkbox_field("taxes_yes", 304.56, 112.44, width=13.44, height=12.24, page=0))
	fields.append(checkbox_field("taxes_no", 345.24, 111.84, width=13.32, height=12.24, page=0))
	fields.append(comb_in_cell("sheets_attached", 390.07, 108.50, 2, slot_w=14.16, box_h=10.32, page=0))
	# Item 5 ATC WW010 is preprinted on the published face PDF.

	# Item 6 TIN groups sit on the inner writing band (y=144.62), not the top rule at 142.10.
	fields.append(comb_in_cell("tin_1", 232.85, 144.62, 3, slot_w=14.40, box_h=10.32, page=0))
	fields.append(comb_in_cell("tin_2", 290.21, 144.62, 3, slot_w=14.40, box_h=10.32, page=0))
	fields.append(comb_in_cell("tin_3", 347.59, 144.62, 3, slot_w=14.40, box_h=10.32, page=0))
	fields.append(comb_in_cell("tin_4", 404.95, 144.62, 5, slot_w=14.40, box_h=10.32, page=0))
	fields.append(comb_in_cell("rdo_code", 548.86, 144.62, 3, slot_w=14.88, box_h=10.32, page=0))
	# Name / address: character ticks at y=178.1 and y=204.38, below the item 8/9 labels.
	fields.append(text_on_ticks("taxpayer_name", 23.04, 178.10, 560.0, page=0))
	fields.append(text_on_ticks("registered_address", 23.04, 204.38, 430.0, page=0))
	fields.append(comb_field("zip_code", 533.86, 214.00, 4, slot_w=15.12, height=12.0, page=0))
	fields.append(text_field("contact_number", 104.42, 233.10, 168.0, 12.0, page=0))
	fields.append(checkbox_field("category_private", 447.48, 230.40, width=13.32, height=11.52, page=0))
	fields.append(checkbox_field("category_government", 519.60, 230.40, width=13.44, height=11.52, page=0))
	fields.append(text_field("email", 104.42, 250.90, 480.0, 12.0, page=0))
	fields.append(checkbox_field("relief_yes", 175.20, 265.92, width=13.44, height=11.52, page=0))
	fields.append(checkbox_field("relief_no", 218.64, 265.80, width=13.44, height=11.52, page=0))

	for item, y in ITEM_Y.items():
		fields.append(amount_in_cell(f"item_{item}", AMOUNT_X, y, AMOUNT_W, box_h=9.24, page=0))

	fields.append(text_field("signatory_name", 310.13, 724.20, 278.0, 12.0, page=0))
	fields.append(text_field("signatory_title", 310.13, 733.40, 278.0, 12.0, page=0))

	# Page 2 header: labels at y≈82.7–92.4, writing ticks at y=102.14.
	fields.append(text_on_ticks("tin_p2", 23.04, 102.14, 190.0, page=1))
	fields.append(text_on_ticks("taxpayer_name_p2", 223.85, 102.14, 364.0, page=1))
	return fields


def values_from_context(ctx: dict) -> dict[str, str]:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import (
		checkbox,
		digits_only,
		format_amount,
		format_tin_display,
		split_tin,
	)

	values: dict[str, str] = {}
	year = int(ctx.get("year") or 0)
	month = int(ctx.get("month") or 0)
	tin_1, tin_2, tin_3, tin_4 = split_tin(ctx.get("tin"), ctx.get("tin_branch"))
	values["month"] = f"{month:02d}" if month else ""
	values["year"] = f"{year:04d}" if year else ""
	values["month_1"] = values["month"][:1]
	values["month_2"] = values["month"][1:2]
	for index, digit in enumerate(values["year"], start=1):
		values[f"year_{index}"] = digit
	values["amended_no"] = checkbox(True)
	values["taxes_yes"] = checkbox(bool(ctx.get("any_taxes_withheld")))
	values["taxes_no"] = checkbox(not ctx.get("any_taxes_withheld"))
	values["sheets_attached"] = "00"
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
	values["relief_no"] = checkbox(True)
	values["signatory_name"] = (ctx.get("signatory_name") or "").upper()
	values["signatory_title"] = (ctx.get("signatory_title") or "").upper()
	values["tin_p2"] = format_tin_display(ctx.get("tin"), ctx.get("tin_branch"))
	values["taxpayer_name_p2"] = values["taxpayer_name"]
	for item in ITEM_Y:
		values[f"item_{item}"] = format_amount(ctx.get(f"item_{item}") or 0)
	return values


def write_fillable_pdf(source_path: str | None = None, dest_path: str | None = None) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import write_fillable_pdf as convert_pdf

	return convert_pdf(
		source_path or get_source_pdf_path(),
		dest_path or get_fillable_pdf_path(),
		get_field_layout(),
	)
