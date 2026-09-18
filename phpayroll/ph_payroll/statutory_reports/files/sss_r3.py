# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.utils import flt, getdate


def sss_r3_dat(employer, rows, year, month) -> str:
	"""Collection list for SSS R3 File Generator / My.SSS upload.

	Columns: SSSNo, Last, First, Middle, SS_EE, SS_ER, EC, WISP_EE, WISP_ER, Remarks, DateHired
	Remarks: N normal, 1 new hire this month, 2 separated this month.
	"""
	lines = [
		"SSSNo,LastName,FirstName,MiddleName,SS_EE,SS_ER,EC,WISP_EE,WISP_ER,Remarks,DateHiredOrSeparated"
	]
	period_start = getdate(f"{int(year)}-{int(month):02d}-01")
	from calendar import monthrange

	period_end = getdate(f"{int(year)}-{int(month):02d}-{monthrange(int(year), int(month))[1]}")
	for row in rows:
		remarks = "N"
		stamp = ""
		joined = getdate(row.get("date_of_joining")) if row.get("date_of_joining") else None
		left = getdate(row.get("relieving_date")) if row.get("relieving_date") else None
		if joined and period_start <= joined <= period_end:
			remarks = "1"
			stamp = joined.strftime("%m%d%Y")
		elif left and period_start <= left <= period_end:
			remarks = "2"
			stamp = left.strftime("%m%d%Y")
		lines.append(
			",".join(
				[
					str(row.get("sss_no") or "").replace("-", "").replace(" ", ""),
					str(row.get("last_name") or "").replace(",", " "),
					str(row.get("first_name") or "").replace(",", " "),
					str(row.get("middle_name") or "").replace(",", " "),
					f"{flt(row.get('ss_ee')):.2f}",
					f"{flt(row.get('ss_er')):.2f}",
					f"{flt(row.get('ec_er')):.2f}",
					f"{flt(row.get('wisp_ee')):.2f}",
					f"{flt(row.get('wisp_er')):.2f}",
					remarks,
					stamp,
				]
			)
		)
	header = (
		f"EmployerID,{employer.sss_employer_no or ''}\n"
		f"EmployerName,{(employer.registered_name or '').replace(',', ' ')}\n"
		f"ApplicableMonth,{int(month):02d}{int(year)}\n"
	)
	return header + "\n".join(lines) + "\n"
