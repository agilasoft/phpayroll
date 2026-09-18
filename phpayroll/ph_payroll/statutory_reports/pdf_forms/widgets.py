# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""AcroForm helpers that follow pdffiller's Design Fields conversion."""

from __future__ import annotations

import os

DIGIT_HEIGHT = 13.0
DIGIT_FONT = 9.0
TEXT_FONT = 8.0
AMOUNT_FONT = 8.0
# pdffiller Design Fields reject text widgets shorter than 12pt.
WIDGET_MIN_H = 12.0
# PyMuPDF widget appearances paint above rect.y0; extra inset seats glyphs in the cell.
COMB_BIAS = 1.8
TEXT_BIAS = 2.6


def inset_y(box_y, box_h, font_size, bias=None):
	"""Shift origin down so top-aligned glyphs sit in the printed cell, not on its top rule."""
	box_h = float(box_h)
	font_size = float(font_size)
	pad = max((box_h - font_size) / 2.0, 0.0)
	if bias is None:
		# Short comb cells need a larger AP correction; taller cells are already padded.
		bias = COMB_BIAS if box_h <= 12.5 else TEXT_BIAS
	return float(box_y) + pad + float(bias)


def comb_in_cell(name, x, box_y, slots, slot_w, box_h=10.32, font_size=DIGIT_FONT, page=0):
	return comb_field(
		name,
		x,
		inset_y(box_y, box_h, font_size),
		slots,
		slot_w=slot_w,
		height=WIDGET_MIN_H,
		font_size=font_size,
		page=page,
	)


def digit_cell(name, box_x, box_y, box_w=13.92, box_h=10.32, page=0):
	"""One digit centered in a printed BIR cell (avoids comb left-align on the box rule)."""
	widget_w = 10.0
	x = float(box_x) + (float(box_w) - widget_w) / 2.0
	field = comb_in_cell(name, x, box_y, 1, slot_w=widget_w, box_h=box_h, page=page)
	field["align"] = "center"
	return field


def text_on_ticks(name, x, tick_y, width, font_size=TEXT_FONT, page=0, align="left"):
	"""Place a line of text in the writing band that ends at the tick marks.

	tick_y is the top of the printed ticks (typically 5.76pt tall). The widget is
	12pt minimum, so it is bottom-aligned to the ticks instead of starting on
	them and overflowing the next label.
	"""
	tick_h = 5.76
	y = float(tick_y) + tick_h - WIDGET_MIN_H
	return text_field(
		name,
		x,
		y,
		width,
		WIDGET_MIN_H,
		font_size=font_size,
		page=page,
		align=align,
	)


def text_in_cell(name, x, box_y, width, box_h=15.0, font_size=TEXT_FONT, page=0, align="left"):
	return text_field(
		name,
		x,
		inset_y(box_y, box_h, font_size, bias=TEXT_BIAS),
		width,
		WIDGET_MIN_H,
		font_size=font_size,
		page=page,
		align=align,
	)


def amount_in_cell(name, x, box_y, width, box_h=9.24, page=0):
	return amount_field(
		name,
		x,
		inset_y(box_y, box_h, AMOUNT_FONT),
		width,
		height=WIDGET_MIN_H,
		page=page,
	)


def comb_field(name, x, y, slots, slot_w=14.0, height=DIGIT_HEIGHT, font_size=DIGIT_FONT, page=0):
	return {
		"field_name": name,
		"field_type": "Data",
		"page": page,
		"x": x,
		"y": y,
		"width": slot_w * slots,
		"height": height,
		"font_size": font_size,
		"text_maxlen": slots,
		"comb": 1,
		"editable": 0,
		"source_type": "Field Path",
	}


def text_field(name, x, y, width, height, font_size=TEXT_FONT, page=0, align="left"):
	return {
		"field_name": name,
		"field_type": "Data",
		"page": page,
		"x": x,
		"y": y,
		"width": width,
		"height": height,
		"font_size": font_size,
		"editable": 0,
		"align": align,
		"source_type": "Field Path",
	}


def amount_field(name, x, y, width, height=15.0, page=0):
	return text_field(name, x, y, width, height, font_size=AMOUNT_FONT, page=page, align="right")


def checkbox_field(name, x, y, size=12.0, page=0, width=None, height=None):
	return {
		"field_name": name,
		"field_type": "Check",
		"page": page,
		"x": x,
		"y": y,
		"width": width if width is not None else size,
		"height": height if height is not None else size,
		"editable": 0,
		"font_size": 10,
		"source_type": "Field Path",
	}


def listing_text(name, x, y, width, page=0, font_size=7.0, align="left"):
	"""Dense row text that still meets the 12pt Design Fields minimum height."""
	return text_field(
		name,
		x,
		float(y),
		width,
		WIDGET_MIN_H,
		font_size=font_size,
		page=page,
		align=align,
	)


def repeat_data_pages(source_path: str, dest_path: str, copies: int, data_page: int = 0) -> str:
	"""Stack ``copies`` of the official data page, then keep instruction pages."""
	import fitz

	if not os.path.exists(source_path):
		raise FileNotFoundError(f"Official source PDF is missing: {source_path}")
	copies = max(1, int(copies))
	src = fitz.open(source_path)
	out = fitz.open()
	try:
		for _ in range(copies):
			out.insert_pdf(src, from_page=data_page, to_page=data_page)
		for page in range(src.page_count):
			if page != data_page:
				out.insert_pdf(src, from_page=page, to_page=page)
		dest_dir = os.path.dirname(dest_path)
		if dest_dir:
			os.makedirs(dest_dir, exist_ok=True)
		out.save(dest_path)
	finally:
		out.close()
		src.close()
	return dest_path


def pad_field_for_designer(field: dict) -> dict:
	"""Meet pdffiller.utils.pdf_designer min width/height without shifting origin."""
	out = dict(field)
	field_type = out.get("field_type") or "Data"
	if field_type in ("Check", "CheckBox", "Checkbox"):
		out["field_type"] = "Check"
		out["width"] = max(float(out["width"]), 12.0)
		out["height"] = max(float(out["height"]), 10.0)
	else:
		out["width"] = max(float(out["width"]), 10.0)
		out["height"] = max(float(out["height"]), 12.0)
	out.setdefault("font_size", TEXT_FONT)
	out.setdefault("editable", 0)
	out.setdefault("source_type", "Field Path")
	if "align" in field:
		out["align"] = field["align"]
	return out


def write_fillable_pdf(source_path: str, dest_path: str, fields: list[dict]) -> str:
	"""Convert a published BIR PDF into a fillable PDF the same way pdffiller does.

	pdffiller Design Fields: open the source, drop existing widgets, stamp the
	layout with ``apply_field_layout``, then save the AcroForm PDF.
	"""
	from pdffiller.utils.pdf_designer import apply_field_layout

	if not os.path.exists(source_path):
		raise FileNotFoundError(f"Official source PDF is missing: {source_path}")

	layout = [pad_field_for_designer(field) for field in fields]
	pdf_bytes = _apply_text_align(apply_field_layout(source_path, layout), layout)
	dest_dir = os.path.dirname(dest_path)
	if dest_dir:
		os.makedirs(dest_dir, exist_ok=True)
	with open(dest_path, "wb") as handle:
		handle.write(pdf_bytes)
	return dest_path


def _apply_text_align(pdf_bytes: bytes, layout: list[dict]) -> bytes:
	"""pdffiller's designer does not stamp Q alignment; set it on amount/text widgets."""
	import fitz

	aligns = {
		field["field_name"]: field.get("align")
		for field in layout
		if field.get("align") and field.get("align") != "left"
	}
	if not aligns:
		return pdf_bytes
	doc = fitz.open(stream=pdf_bytes, filetype="pdf")
	try:
		changed = False
		for page in doc:
			for widget in page.widgets() or []:
				align = aligns.get(widget.field_name)
				if not align:
					continue
				q = {"center": "1", "right": "2"}.get(align)
				if not q:
					continue
				doc.xref_set_key(widget.xref, "Q", q)
				changed = True
		return doc.tobytes(garbage=4, deflate=True) if changed else pdf_bytes
	finally:
		doc.close()
