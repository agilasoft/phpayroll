# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Iterable, Sequence

from frappe.utils import flt, getdate


def strip_tin(tin) -> str:
	if not tin:
		return ""
	return "".join(ch for ch in str(tin) if ch.isdigit())


def format_amount(value) -> str:
	return f"{flt(value):.2f}"


def _format_field(value) -> str:
	if value is None:
		return ""
	if isinstance(value, (int, float)) and not isinstance(value, bool):
		return format_amount(value)
	return str(value).replace("\n", " ").replace("\r", " ").replace(",", " ").strip()


def encode_row(prefix: str, fields: Sequence) -> str:
	return prefix + "," + ",".join(_format_field(f) for f in fields)


def build_header_trailer_dat(
	*,
	tin: str,
	branch: str,
	registered_name: str,
	registered_address: str,
	form_type: str,
	period_from,
	period_to,
	detail_rows: Iterable[Sequence],
) -> str:
	pf = getdate(period_from)
	pt = getdate(period_to)
	tin = strip_tin(tin)
	branch = (branch or "000").zfill(3)
	lines = [
		encode_row(
			"H",
			[
				tin,
				branch,
				registered_name,
				registered_address,
				form_type,
				pf.strftime("%m%d%Y"),
				pt.strftime("%m%d%Y"),
			],
		)
	]
	count = 0
	for row in detail_rows:
		lines.append(encode_row("A", row))
		count += 1
	lines.append(encode_row("T", [tin, branch, form_type, count]))
	return "\n".join(lines) + "\n"


def bir_1601c_dat(employer, rows, period_from, period_to) -> str:
	detail = []
	for row in rows:
		detail.append(
			[
				strip_tin(row.get("tin")),
				"000",
				row.get("employee_name") or "",
				(row.get("current_address") or row.get("permanent_address") or ""),
				"WI010",
				0,
				row.get("taxable") or 0,
				row.get("tax") or 0,
			]
		)
	return build_header_trailer_dat(
		tin=employer.tin,
		branch=employer.tin_branch_code,
		registered_name=employer.registered_name,
		registered_address=employer.registered_address,
		form_type="1601C",
		period_from=period_from,
		period_to=period_to,
		detail_rows=detail,
	)


def bir_1604c_dat(employer, rows, year) -> str:
	"""Employee alphalist DAT for BIR 1604-C. Validate in Alphalist Data Entry Module."""
	period_from = f"{int(year)}-01-01"
	period_to = f"{int(year)}-12-31"
	detail = []
	for row in rows:
		detail.append(
			[
				strip_tin(row.get("tin")),
				"000",
				row.get("last_name") or "",
				row.get("first_name") or "",
				row.get("middle_name") or "",
				(row.get("current_address") or row.get("permanent_address") or ""),
				row.get("zip_code") or "",
				1 if row.get("is_mwe") else 0,
				row.get("taxable") or 0,
				row.get("thirteenth") or 0,
				flt(row.get("ss_ee")) + flt(row.get("ph_ee")) + flt(row.get("hd_ee")),
				row.get("tax") or 0,
				getdate(row.get("date_of_joining")).strftime("%m%d%Y") if row.get("date_of_joining") else "",
				getdate(row.get("relieving_date")).strftime("%m%d%Y") if row.get("relieving_date") else "",
			]
		)
	return build_header_trailer_dat(
		tin=employer.tin,
		branch=employer.tin_branch_code,
		registered_name=employer.registered_name,
		registered_address=employer.registered_address,
		form_type="1604C",
		period_from=period_from,
		period_to=period_to,
		detail_rows=detail,
	)
