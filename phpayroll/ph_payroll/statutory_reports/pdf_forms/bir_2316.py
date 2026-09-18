# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""BIR Form 2316 September 2021 (ENCS): overlay fillable fields on the official PDF."""

from __future__ import annotations

import os

from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import (
	amount_in_cell,
	checkbox_field,
	comb_in_cell,
	text_in_cell,
)

RIGHT_X = 483.84
RIGHT_W = 101.74
LEFT_X = 207.45
LEFT_W = 101.77
RIGHT_ITEMS = {
	29: 141.44,
	30: 160.47,
	31: 180.41,
	32: 200.63,
	33: 220.62,
	34: 240.05,
	35: 259.0,
	36: 278.5,
	37: 297.7,
	38: 316.7,
	39: 354.5,
	40: 374.0,
	41: 392.9,
	42: 412.4,
	43: 431.4,
	45: 503.1,
	46: 521.9,
	47: 541.4,
	48: 560.8,
	49: 580.2,
	50: 599.7,
	52: 667.4,
}
LEFT_ITEMS = {
	"19": 512.21,
	"20": 531.65,
	"21": 551.09,
	"22": 570.53,
	"23": 589.60,
	"24": 609.04,
	"25a": 628.48,
	"25b": 648.29,
	"26": 667.74,
	"27": 687.63,
	"28": 707.11,
}


def _pdf_dir():
	return os.path.normpath(
		os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "public", "pdf")
	)


def get_source_pdf_path():
	return os.path.join(_pdf_dir(), "bir_form_2316_september_2021_encs.pdf")


def get_fillable_pdf_path():
	return os.path.join(_pdf_dir(), "bir_form_2316_fillable.pdf")


def context_from_filters(filters):
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.context import get_2316_context

	return get_2316_context(filters)


def _tin_fields(prefix: str, box_y: float) -> list[dict]:
	return [
		comb_in_cell(f"{prefix}_tin_1", 86.24, box_y, 3, slot_w=12.64, box_h=15.05, page=0),
		comb_in_cell(f"{prefix}_tin_2", 135.88, box_y, 3, slot_w=12.64, box_h=15.05, page=0),
		comb_in_cell(f"{prefix}_tin_3", 185.55, box_y, 3, slot_w=12.64, box_h=15.05, page=0),
		comb_in_cell(f"{prefix}_tin_4", 235.22, box_y, 5, slot_w=14.17, box_h=15.05, page=0),
	]


def get_field_layout() -> list[dict]:
	fields: list[dict] = []
	fields.append(comb_in_cell("year", 124.78, 94.29, 4, slot_w=17.72, box_h=15.14, page=0))
	fields.append(comb_in_cell("period_from", 386.81, 94.59, 4, slot_w=17.46, box_h=14.81, page=0))
	fields.append(comb_in_cell("period_to", 512.38, 94.59, 4, slot_w=17.49, box_h=14.81, page=0))
	fields.extend(_tin_fields("ee", 122.72))
	fields.append(text_in_cell("employee_name", 42.21, 148.46, 211.40, box_h=15.04, page=0))
	fields.append(comb_in_cell("rdo_code", 264.49, 148.46, 3, slot_w=12.66, box_h=15.04, page=0))
	fields.append(text_in_cell("registered_address", 42.63, 176.64, 210.98, box_h=14.76, page=0))
	fields.append(comb_in_cell("zip_code", 261.42, 176.71, 4, slot_w=12.00, box_h=14.76, page=0))
	fields.append(text_in_cell("home_address", 42.63, 201.90, 210.98, box_h=14.76, page=0))
	fields.append(comb_in_cell("home_zip", 261.51, 201.76, 4, slot_w=11.98, box_h=14.79, page=0))
	fields.append(text_in_cell("foreign_address", 42.63, 227.37, 266.80, box_h=15.02, page=0))
	fields.append(comb_in_cell("date_of_birth", 46.90, 254.10, 8, slot_w=12.58, box_h=14.60, page=0))
	fields.append(text_in_cell("contact_number", 167.20, 254.20, 142.20, box_h=14.90, page=0))
	fields.append(amount_in_cell("smw_day", 209.90, 272.30, 98.70, box_h=14.80, page=0))
	fields.append(amount_in_cell("smw_month", 209.90, 290.70, 98.70, box_h=14.80, page=0))
	fields.append(checkbox_field("is_mwe", 47.70, 309.90, width=13.70, height=12.50, page=0))

	fields.extend(_tin_fields("er", 335.24))
	fields.append(text_in_cell("employer_name", 42.21, 360.98, 266.15, box_h=15.00, page=0))
	fields.append(text_in_cell("employer_address", 42.63, 387.21, 210.98, box_h=14.92, page=0))
	fields.append(comb_in_cell("employer_zip", 259.33, 388.06, 4, slot_w=12.00, box_h=14.14, page=0))
	fields.append(checkbox_field("main_employer", 115.89, 406.15, width=13.75, height=12.58, page=0))
	fields.append(checkbox_field("secondary_employer", 199.64, 406.15, width=13.75, height=12.58, page=0))

	for item, y in RIGHT_ITEMS.items():
		fields.append(amount_in_cell(f"item_{item}", RIGHT_X, y, RIGHT_W, box_h=14.90, page=0))
	fields.append(amount_in_cell("item_44", RIGHT_X, 458.80, RIGHT_W, box_h=15.40, page=0))
	fields.append(amount_in_cell("item_51a", RIGHT_X, 628.80, RIGHT_W, box_h=15.40, page=0))
	fields.append(amount_in_cell("item_51b", RIGHT_X, 648.30, RIGHT_W, box_h=15.40, page=0))
	for item, y in LEFT_ITEMS.items():
		fields.append(amount_in_cell(f"item_{item}", LEFT_X, y, LEFT_W, box_h=15.40, page=0))

	fields.append(text_in_cell("signatory_name", 75.84, 760.32, 250.75, box_h=9.84, page=0))
	fields.append(comb_in_cell("date_signed_er", 415.71, 756.66, 8, slot_w=12.61, box_h=14.77, page=0))
	fields.append(checkbox_field("substituted_filing", 367.90, 904.00, width=13.90, height=12.00, page=0))
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
	ee1, ee2, ee3, ee4 = split_tin(ctx.get("employee_tin"))
	er1, er2, er3, er4 = split_tin(ctx.get("tin"), ctx.get("tin_branch"))
	values["year"] = f"{year:04d}" if year else ""
	values["period_from"] = digits_only(ctx.get("period_from"), 4)
	values["period_to"] = digits_only(ctx.get("period_to"), 4)
	values["ee_tin_1"] = ee1
	values["ee_tin_2"] = ee2
	values["ee_tin_3"] = ee3
	values["ee_tin_4"] = ee4
	values["employee_name"] = (ctx.get("employee_name") or "").upper()
	values["rdo_code"] = digits_only(ctx.get("rdo_code"), 3)
	values["registered_address"] = (ctx.get("employee_address") or "").upper()
	values["zip_code"] = digits_only(ctx.get("employee_zip"), 4)
	values["home_address"] = values["registered_address"]
	values["home_zip"] = values["zip_code"]
	values["date_of_birth"] = digits_only(ctx.get("date_of_birth"), 8)
	values["contact_number"] = digits_only(ctx.get("contact_number"))
	values["is_mwe"] = checkbox(bool(ctx.get("is_mwe")))
	values["er_tin_1"] = er1
	values["er_tin_2"] = er2
	values["er_tin_3"] = er3
	values["er_tin_4"] = er4
	values["employer_name"] = (ctx.get("registered_name") or "").upper()
	values["employer_address"] = (ctx.get("registered_address") or "").upper()
	values["employer_zip"] = digits_only(ctx.get("zip"), 4)
	values["main_employer"] = checkbox(True)
	values["signatory_name"] = (ctx.get("signatory_name") or "").upper()
	values["substituted_filing"] = checkbox(bool(ctx.get("substituted_filing")))

	amount_keys = [str(key) for key in RIGHT_ITEMS] + list(LEFT_ITEMS) + ["44", "51a", "51b"]
	for item in amount_keys:
		key = f"item_{item}"
		values[key] = format_amount(ctx.get(key) or 0, blank_if_zero=True)
	return values


def write_fillable_pdf(source_path: str | None = None, dest_path: str | None = None) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms.widgets import write_fillable_pdf as convert_pdf

	return convert_pdf(
		source_path or get_source_pdf_path(),
		dest_path or get_fillable_pdf_path(),
		get_field_layout(),
	)
