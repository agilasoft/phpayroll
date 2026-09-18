# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.utils import flt


def pagibig_mcrf_xls_rows(employer, rows, year, month):
	"""Rows for Virtual Pag-IBIG MCRF XLS (header + members)."""
	period = f"{int(year)}{int(month):02d}"
	out = [
		["Employer ID", employer.pagibig_employer_id or ""],
		["Employer Name", employer.registered_name or ""],
		["Period", period],
		[],
		["MID", "Last Name", "First Name", "Middle Name", "Period", "EE", "ER", "Total"],
	]
	for row in rows:
		ee = flt(row.get("hd_ee"))
		er = flt(row.get("hd_er"))
		out.append(
			[
				str(row.get("hdmf_no") or "").replace("-", "").replace(" ", ""),
				row.get("last_name") or "",
				row.get("first_name") or "",
				row.get("middle_name") or "",
				period,
				round(ee, 2),
				round(er, 2),
				round(ee + er, 2),
			]
		)
	return out


def pagibig_mcrf_csv(employer, rows, year, month) -> str:
	lines = []
	for i, row in enumerate(pagibig_mcrf_xls_rows(employer, rows, year, month)):
		lines.append(",".join("" if c is None else str(c).replace(",", " ") for c in row))
	return "\n".join(lines) + "\n"
