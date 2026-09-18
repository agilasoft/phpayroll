# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.utils import flt


def philhealth_rf1_csv(employer, rows, year, month) -> str:
	"""EPRS-style employee remittance CSV."""
	period = f"{int(year)}{int(month):02d}"
	lines = ["PIN,LastName,FirstName,MiddleName,Period,EE,ER,Total"]
	for row in rows:
		ee = flt(row.get("ph_ee"))
		er = flt(row.get("ph_er"))
		lines.append(
			",".join(
				[
					str(row.get("phic_no") or "").replace("-", "").replace(" ", ""),
					str(row.get("last_name") or "").replace(",", " "),
					str(row.get("first_name") or "").replace(",", " "),
					str(row.get("middle_name") or "").replace(",", " "),
					period,
					f"{ee:.2f}",
					f"{er:.2f}",
					f"{ee + er:.2f}",
				]
			)
		)
	header = (
		f"PEN,{employer.philhealth_pen or ''}\n"
		f"EmployerName,{(employer.registered_name or '').replace(',', ' ')}\n"
	)
	return header + "\n".join(lines) + "\n"
