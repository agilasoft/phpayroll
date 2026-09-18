# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Fill official BIR / SSS / PhilHealth / Pag-IBIG PDFs via pdffiller."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import tempfile

import frappe
from frappe import _

CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.json")

PRINTABLE_FORMS = {
	"1601C": "phpayroll.ph_payroll.statutory_reports.pdf_forms.bir_1601c",
	"1604C": "phpayroll.ph_payroll.statutory_reports.pdf_forms.bir_1604c",
	"2316": "phpayroll.ph_payroll.statutory_reports.pdf_forms.bir_2316",
	"SSS_R3": "phpayroll.ph_payroll.statutory_reports.pdf_forms.sss_r3",
	"PHIC_RF1": "phpayroll.ph_payroll.statutory_reports.pdf_forms.phic_rf1",
	"HDMF_MCRF": "phpayroll.ph_payroll.statutory_reports.pdf_forms.hdmf_mcrf",
}

BIR_FORMS = PRINTABLE_FORMS

FORM_ALIASES = {
	"1601C": "1601C",
	"1601-C": "1601C",
	"BIR 1601-C": "1601C",
	"1604C": "1604C",
	"1604-C": "1604C",
	"BIR 1604-C": "1604C",
	"2316": "2316",
	"BIR 2316": "2316",
	"SSS_R3": "SSS_R3",
	"SSS R-3": "SSS_R3",
	"R-3": "SSS_R3",
	"PHIC_RF1": "PHIC_RF1",
	"RF1": "PHIC_RF1",
	"RF-1": "PHIC_RF1",
	"HDMF_MCRF": "HDMF_MCRF",
	"MCRF": "HDMF_MCRF",
	"MSRF": "HDMF_MCRF",
}


def load_catalog() -> dict:
	with open(CATALOG_PATH, encoding="utf-8") as handle:
		return json.load(handle)


def _bundled_pdf_path(filename: str) -> str:
	return os.path.join(frappe.get_app_path("phpayroll"), "public", "pdf", filename)


def _form_module(form: str):
	path = PRINTABLE_FORMS.get(form)
	if not path:
		frappe.throw(_("Unsupported form {0}").format(form))
	return frappe.get_module(path)


def ensure_fillable_pdf(form: str) -> str:
	from phpayroll.ph_payroll.statutory_reports.pdf_forms import widgets as widget_mod

	mod = _form_module(form)
	source = mod.get_source_pdf_path()
	path = mod.get_fillable_pdf_path()
	inputs = [source, os.path.abspath(mod.__file__), os.path.abspath(widget_mod.__file__)]
	if os.path.exists(path) and all(os.path.exists(p) for p in inputs):
		if os.path.getmtime(path) >= max(os.path.getmtime(p) for p in inputs):
			return path
	try:
		return mod.write_fillable_pdf()
	except OSError:
		import tempfile

		return mod.write_fillable_pdf(dest_path=os.path.join(tempfile.gettempdir(), os.path.basename(path)))


def fill_printable_pdf(
	filters, form: str, fields_only: bool = False, overrides: dict | None = None
) -> tuple[bytes, dict]:
	from pdffiller.utils.pdf_filler import fill_pdf, fill_pdf_fields_only

	mod = _form_module(form)
	ctx = mod.context_from_filters(filters)
	copies = 1
	if getattr(mod, "ROWS_PER_PAGE", None):
		count = len(ctx.get("employees") or [])
		copies = max(1, math.ceil(count / mod.ROWS_PER_PAGE) if count else 1)
		pdf_path = mod.write_fillable_pdf(
			dest_path=os.path.join(tempfile.gettempdir(), f"phpayroll_{form}_{copies}_fillable.pdf"),
			copies=copies,
		)
		values = mod.values_from_context(ctx, copies=copies)
	else:
		pdf_path = ensure_fillable_pdf(form)
		values = mod.values_from_context(ctx)
	if overrides:
		values.update({str(key): str(value or "") for key, value in overrides.items()})
	if fields_only:
		return fill_pdf_fields_only(pdf_path, values), values
	return fill_pdf(pdf_path, values, readonly_fields=set(values)), values


def preview_fields(values: dict) -> list[dict]:
	return [
		{
			"pdf_field_name": name,
			"value": value or "",
			"editable": 0,
			"source_type": "Field Path",
		}
		for name, value in values.items()
	]


def _resolve_mappings(dotted_path: str | None) -> list[dict]:
	if not dotted_path:
		return []
	resolver = frappe.get_attr(dotted_path)
	return list(resolver() or [])


def _layout_as_mappings(form: str) -> list[dict]:
	mod = _form_module(form)
	rows = []
	for field in mod.get_field_layout():
		rows.append(
			{
				"pdf_field_name": field["field_name"],
				"source_type": "Field Path",
				"source_field": field["field_name"],
			}
		)
	return rows


def sync_payroll_pdf_forms():
	"""Attach official BIR PDFs and stamp pdffiller field layouts onto PDF Form Templates."""
	if "pdffiller" not in frappe.get_installed_apps():
		return
	if not frappe.db.exists("DocType", "PDF Form Template"):
		return

	catalog = load_catalog()
	group = catalog.get("group") or "PH Statutory Forms"
	for form in catalog.get("forms") or []:
		form_number = (form.get("form_number") or "").upper()
		if form_number not in PRINTABLE_FORMS:
			continue
		source_name = form.get("source_pdf_filename")
		if not source_name:
			continue
		source_path = _bundled_pdf_path(source_name)
		if not os.path.exists(source_path):
			frappe.log_error(
				title="phpayroll BIR PDF form missing",
				message=f"Official BIR PDF not found: {source_path}",
			)
			continue
		try:
			fillable_path = ensure_fillable_pdf(form_number)
		except Exception:
			frappe.log_error(title=f"phpayroll {form_number} fillable PDF failed")
			continue
		with open(fillable_path, "rb") as handle:
			pdf_content = handle.read()
		mappings = _resolve_mappings(form.get("mappings")) or _layout_as_mappings(form_number)
		pdf_filename = os.path.basename(fillable_path)
		for template in form.get("templates") or []:
			title = (template.get("title") or "").strip()
			doctype = (template.get("reference_doctype") or "").strip()
			if not title or not doctype:
				continue
			_upsert_template(
				title=title,
				reference_doctype=doctype,
				group=group,
				pdf_filename=pdf_filename,
				pdf_content=pdf_content,
				mappings=mappings,
			)
	frappe.clear_cache()


def _find_template(title: str, reference_doctype: str) -> str | None:
	return frappe.db.get_value(
		"PDF Form Template",
		{"title": title, "reference_doctype": reference_doctype},
		"name",
	) or frappe.db.get_value("PDF Form Template", {"title": title}, "name")


def _upsert_template(*, title, reference_doctype, group, pdf_filename, pdf_content, mappings):
	existing_name = _find_template(title, reference_doctype)
	if existing_name:
		doc = frappe.get_doc("PDF Form Template", existing_name)
	else:
		doc = frappe.new_doc("PDF Form Template")
		doc.title = title
		doc.reference_doctype = reference_doctype
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
	doc.reference_doctype = reference_doctype
	doc.group = group
	doc.show_on_draft = 0
	doc.fields_only = 0
	_attach_pdf(doc, pdf_filename, pdf_content)
	doc.set("field_mappings", [])
	for row in mappings:
		doc.append("field_mappings", row)
	doc.flags.ignore_mandatory = False
	doc.save(ignore_permissions=True)


def _attach_pdf(doc, pdf_filename: str, pdf_content: bytes):
	from frappe.utils.file_manager import get_content_hash, save_file

	if doc.pdf_file:
		existing = frappe.db.get_value(
			"File",
			{"file_url": doc.pdf_file},
			["name", "content_hash"],
			as_dict=True,
		)
		if existing and existing.content_hash == get_content_hash(pdf_content):
			return
	file_doc = save_file(
		fname=pdf_filename,
		content=pdf_content,
		dt="PDF Form Template",
		dn=doc.name,
		df="pdf_file",
		is_private=1,
	)
	doc.pdf_file = file_doc.file_url


def _save_preview_pdf(pdf_bytes: bytes, filename: str) -> str:
	"""Write the filled PDF once and return a private File URL (avoids multi-MB JSON)."""
	from frappe.utils.file_manager import save_file

	safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)[:80] or "form.pdf"
	if not safe.lower().endswith(".pdf"):
		safe = f"{safe}.pdf"
	user = frappe.session.user or "guest"
	token = hashlib.sha1(user.encode()).hexdigest()[:12]
	stored = f"phpayroll-preview-{token}-{safe}"
	for name in frappe.get_all(
		"File",
		filters={"file_name": ["like", f"phpayroll-preview-{token}-%"], "is_private": 1},
		pluck="name",
	):
		try:
			frappe.delete_doc("File", name, ignore_permissions=True, delete_permanently=True)
		except Exception:
			pass
	file_doc = save_file(fname=stored, content=pdf_bytes, dt=None, dn=None, is_private=1)
	return file_doc.file_url


def _pdf_response(pdf_bytes: bytes, filename: str, values: dict, fields_only: bool):
	file_url = None
	try:
		file_url = _save_preview_pdf(pdf_bytes, filename)
	except Exception:
		frappe.log_error(title="PH Payroll printable preview file save failed")
	return {
		"filename": filename,
		"file_url": file_url,
		"data_uri": f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode('ascii')}",
		"fields": preview_fields(values),
		"fields_only": bool(fields_only),
	}


def _normalize_form(form: str) -> str:
	raw = str(form or "").strip()
	return FORM_ALIASES.get(raw.upper(), raw.upper())


def _parse_filters(filters):
	return filters if isinstance(filters, dict) else json.loads(filters or "{}")


@frappe.whitelist()
def export_printable_form(filters, form, fields_only=0, field_overrides=None):
	filters = _parse_filters(filters)
	form = _normalize_form(form)
	overrides = field_overrides or {}
	if isinstance(overrides, str):
		overrides = json.loads(overrides or "{}")

	if form not in PRINTABLE_FORMS:
		frappe.throw(_("Unsupported form {0}").format(form))
	if not filters.get("company") and form != "2316":
		frappe.throw(_("Please select Company"))
	if form in ("1601C", "SSS_R3", "PHIC_RF1", "HDMF_MCRF"):
		if not filters.get("year") or not filters.get("month"):
			frappe.throw(_("Please select Year and Month"))
	elif form in ("1604C", "2316"):
		if not filters.get("year"):
			frappe.throw(_("Please select Year"))
	if form == "2316" and not filters.get("employee"):
		frappe.throw(_("Employee is required for BIR 2316."))
	source = _form_module(form).get_source_pdf_path()
	if not os.path.exists(source):
		frappe.throw(_("Official {0} form PDF is missing.").format(form))
	pdf_bytes, values = fill_printable_pdf(
		filters,
		form,
		fields_only=bool(frappe.utils.cint(fields_only)),
		overrides=overrides,
	)
	if form == "1604C":
		filename = f"BIR_{form}_{filters.get('year')}.pdf"
	elif form == "2316":
		filename = f"BIR_2316_{filters.get('employee')}_{filters.get('year')}.pdf"
	elif form in ("SSS_R3", "PHIC_RF1", "HDMF_MCRF"):
		filename = f"{form}_{filters.get('year')}_{filters.get('month')}.pdf"
	else:
		filename = f"BIR_{form}_{filters.get('year')}_{filters.get('month')}.pdf"
	return _pdf_response(pdf_bytes, filename, values, frappe.utils.cint(fields_only))


@frappe.whitelist()
def export_2316(filters, fields_only=0, field_overrides=None):
	filters = _parse_filters(filters)
	if not filters.get("employee") or not filters.get("year"):
		frappe.throw(_("Employee and Year are required for BIR 2316."))
	if not filters.get("company"):
		filters["company"] = frappe.db.get_value("Employee", filters.get("employee"), "company")
	overrides = field_overrides or {}
	if isinstance(overrides, str):
		overrides = json.loads(overrides or "{}")
	pdf_bytes, values = fill_printable_pdf(
		filters,
		"2316",
		fields_only=bool(frappe.utils.cint(fields_only)),
		overrides=overrides,
	)
	filename = f"BIR_2316_{filters.get('employee')}_{filters.get('year')}.pdf"
	return _pdf_response(pdf_bytes, filename, values, frappe.utils.cint(fields_only))
