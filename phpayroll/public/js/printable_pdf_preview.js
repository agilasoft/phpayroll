// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.provide("phpayroll.printable");

(function () {
	"use strict";

	function download_pdf(payload) {
		const src = payload && (payload.data_uri || payload.object_url || payload.file_url);
		if (!src) {
			return;
		}
		const link = document.createElement("a");
		link.href = src;
		link.download = (payload && payload.filename) || "form.pdf";
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	}

	function print_pdf(payload) {
		const src = payload && (payload.object_url || payload.data_uri || payload.file_url);
		if (!src) {
			return;
		}
		const print_window = window.open(src);
		if (!print_window) {
			frappe.msgprint({
				title: __("Pop-up Blocked"),
				message: __("Please allow pop-ups to print this PDF."),
				indicator: "orange",
			});
			return;
		}
		print_window.addEventListener("load", function () {
			print_window.focus();
			print_window.print();
		});
	}

	function render_field_row(field) {
		const value = frappe.utils.escape_html(field.value || "");
		const label = frappe.utils.escape_html(field.pdf_field_name);
		return `
			<div class="form-group pdffiller-field-group pdffiller-field-readonly">
				<label class="control-label text-muted">${label}</label>
				<div class="pdffiller-readonly-value">${value || __("Empty")}</div>
			</div>
		`;
	}

	function render_form_panel(fields) {
		const fields_html = (fields || []).map(render_field_row).join("");
		return `
			<div class="pdffiller-form-panel">
				<div class="pdffiller-form-panel-header">
					<button type="button" class="btn btn-default btn-xs pdffiller-form-panel-toggle" title="${__(
						"Field Values"
					)}">
						<span class="pdffiller-form-panel-toggle-label">${__("Field Values")}</span>
					</button>
					<div class="pdffiller-form-panel-actions">
						<span class="text-muted small pdffiller-readonly-note">${__("All fields are read-only")}</span>
					</div>
				</div>
				<div class="pdffiller-form-fields">
					${fields_html || `<p class="text-muted">${__("No mapped fields found.")}</p>`}
				</div>
			</div>
		`;
	}

	function preview_styles() {
		return `
			<style>
				.pdffiller-dialog-body { padding: 0 !important; }
				.pdffiller-viewer { display: flex; flex-direction: column; height: 75vh; min-height: 480px; }
				.pdffiller-viewer-toolbar {
					display: flex; align-items: center; justify-content: space-between;
					gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--border-color);
					background: var(--card-bg);
				}
				.pdffiller-fields-only-toggle {
					display: inline-flex; align-items: center; gap: 8px; margin: 0;
					font-weight: normal; cursor: pointer;
				}
				.pdffiller-viewer-toolbar-actions { display: flex; gap: 8px; }
				.pdffiller-viewer-body { display: flex; flex: 1; min-height: 0; }
				.pdffiller-form-wrapper {
					width: 320px; min-width: 280px; border-right: 1px solid var(--border-color);
					background: var(--card-bg); overflow: auto;
				}
				.pdffiller-form-wrapper--collapsed { width: 44px; min-width: 44px; overflow: hidden; }
				.pdffiller-form-wrapper--collapsed .pdffiller-form-fields,
				.pdffiller-form-wrapper--collapsed .pdffiller-form-panel-actions { display: none; }
				.pdffiller-form-wrapper--collapsed .pdffiller-form-panel-toggle-label { display: none; }
				.pdffiller-form-panel { display: flex; flex-direction: column; height: 100%; }
				.pdffiller-form-panel-header {
					display: flex; align-items: center; justify-content: space-between;
					gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--border-color);
				}
				.pdffiller-form-fields { padding: 12px 16px 16px; overflow: auto; }
				.pdffiller-field-readonly .pdffiller-readonly-value {
					padding: 6px 8px; border: 1px solid var(--border-color);
					border-radius: var(--border-radius); background: var(--disabled-control-bg);
					word-break: break-word;
				}
				.pdffiller-viewer-frame { flex: 1; min-height: 0; background: #323639; }
				.pdffiller-viewer-frame iframe {
					display: block; width: 100%; height: 100%; border: 0; background: #323639;
				}
				.pdffiller-loading {
					display: flex; align-items: center; justify-content: center;
					height: 100%; padding: 16px;
				}
			</style>
		`;
	}

	function render_preview_shell() {
		return `
			${preview_styles()}
			<div class="pdffiller-viewer">
				<div class="pdffiller-viewer-toolbar">
					<label class="pdffiller-fields-only-toggle">
						<input type="checkbox" class="pdffiller-fields-only-checkbox" />
						<span>${__("Fields only (no background)")}</span>
					</label>
					<div class="pdffiller-viewer-toolbar-actions">
						<button type="button" class="btn btn-default btn-sm pdffiller-print-btn" disabled>
							${__("Print")}
						</button>
						<button type="button" class="btn btn-primary btn-sm pdffiller-download-btn" disabled>
							${__("Download")}
						</button>
					</div>
				</div>
				<div class="pdffiller-viewer-body">
					<div class="pdffiller-form-wrapper"></div>
					<div class="pdffiller-viewer-frame">
						<div class="pdffiller-loading text-muted">${__("Generating PDF...")}</div>
					</div>
				</div>
			</div>
		`;
	}

	function show_frame_message($frame, message) {
		$frame.html(
			`<div class="pdffiller-loading text-muted">${frappe.utils.escape_html(message)}</div>`
		);
	}

	function object_url_from_data_uri(data_uri) {
		const comma = data_uri.indexOf(",");
		const header = comma >= 0 ? data_uri.slice(0, comma) : "";
		const payload = comma >= 0 ? data_uri.slice(comma + 1) : data_uri;
		const mime = (header.match(/data:([^;]+)/) || [])[1] || "application/pdf";
		const binary = window.atob(payload);
		const bytes = new Uint8Array(binary.length);
		for (let i = 0; i < binary.length; i++) {
			bytes[i] = binary.charCodeAt(i);
		}
		return URL.createObjectURL(new Blob([bytes], { type: mime }));
	}

	function looks_like_pdf_blob(blob) {
		if (!blob || blob.size < 5) {
			return false;
		}
		const type = String(blob.type || "").toLowerCase();
		if (type.indexOf("html") !== -1 || type.indexOf("javascript") !== -1) {
			return false;
		}
		return type.indexOf("pdf") !== -1 || type === "" || type === "application/octet-stream";
	}

	function blob_url_from_payload(payload) {
		if (payload && payload.data_uri) {
			return Promise.resolve(object_url_from_data_uri(payload.data_uri));
		}
		if (payload && payload.file_url) {
			return fetch(payload.file_url, { credentials: "same-origin" }).then(function (res) {
				const type = String(res.headers.get("content-type") || "").toLowerCase();
				if (!res.ok || type.indexOf("html") !== -1) {
					throw new Error("PDF could not be loaded");
				}
				return res.blob();
			}).then(function (blob) {
				if (!looks_like_pdf_blob(blob)) {
					throw new Error("PDF could not be loaded");
				}
				return URL.createObjectURL(blob);
			});
		}
		return Promise.reject(new Error("Could not generate the filled PDF."));
	}

	function revoke_frame_url($frame) {
		const previous = $frame.data("objectUrl");
		if (previous) {
			URL.revokeObjectURL(previous);
			$frame.removeData("objectUrl");
		}
	}

	function render_pdf_frame($frame, payload) {
		revoke_frame_url($frame);
		return blob_url_from_payload(payload)
			.then(function (src) {
				if (!src || src === "undefined") {
					throw new Error("PDF could not be loaded");
				}
				$frame.data("objectUrl", src);
				payload.object_url = src;
				$frame.html(
					`<iframe class="pdffiller-pdf-frame" src="${src}" title="${__(
						"PDF preview"
					)}"></iframe>`
				);
			})
			.catch(function () {
				show_frame_message($frame, __("Could not generate the filled PDF."));
				throw new Error("Could not generate the filled PDF.");
			});
	}

	phpayroll.printable.open_preview = function (opts) {
		const dialog = new frappe.ui.Dialog({
			title: opts.title || __("PDF Form"),
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "pdf_preview" }],
		});
		const state = { fields: [], payload: null, fields_only: false };
		dialog.show();
		dialog.$wrapper.find(".modal-body").addClass("pdffiller-dialog-body");

		const $preview = dialog.fields_dict.pdf_preview.$wrapper;
		$preview.html(render_preview_shell());
		const $viewer = $preview.find(".pdffiller-viewer").first();
		$viewer
			.find(".pdffiller-form-wrapper")
			.addClass("pdffiller-form-wrapper--collapsed")
			.html(render_form_panel([]));

		function bind_actions() {
			$viewer.find(".pdffiller-print-btn").off("click").on("click", function () {
				if (state.payload) print_pdf(state.payload);
			});
			$viewer.find(".pdffiller-download-btn").off("click").on("click", function () {
				if (state.payload) download_pdf(state.payload);
			});
			$viewer.find(".pdffiller-fields-only-checkbox").off("change").on("change", function () {
				state.fields_only = $(this).is(":checked");
				reload();
			});
			$viewer.find(".pdffiller-form-panel-toggle").off("click").on("click", function () {
				$viewer.find(".pdffiller-form-wrapper").toggleClass("pdffiller-form-wrapper--collapsed");
			});
		}

		function reload() {
			const $frame = $viewer.find(".pdffiller-viewer-frame");
			revoke_frame_url($frame);
			show_frame_message($frame, __("Generating PDF..."));
			$viewer.find(".pdffiller-print-btn, .pdffiller-download-btn").prop("disabled", true);
			opts.load(state, function (payload) {
				if (!payload || !(payload.file_url || payload.data_uri)) {
					show_frame_message($frame, __("Could not generate the filled PDF."));
					return;
				}
				state.payload = payload;
				state.fields = payload.fields || [];
				const collapsed = $viewer
					.find(".pdffiller-form-wrapper")
					.hasClass("pdffiller-form-wrapper--collapsed");
				$viewer.find(".pdffiller-form-wrapper").html(render_form_panel(state.fields));
				if (collapsed) {
					$viewer.find(".pdffiller-form-wrapper").addClass("pdffiller-form-wrapper--collapsed");
				}
				render_pdf_frame($frame, payload)
					.then(function () {
						$viewer.find(".pdffiller-print-btn, .pdffiller-download-btn").prop("disabled", false);
						bind_actions();
					})
					.catch(function () {
						frappe.msgprint({
							title: __("Error"),
							message: __("Could not generate the filled PDF."),
							indicator: "red",
						});
					});
			});
		}

		dialog.onhide = function () {
			revoke_frame_url($viewer.find(".pdffiller-viewer-frame"));
		};

		bind_actions();
		reload();
		return dialog;
	};

	phpayroll.printable.preview_form = function (opts) {
		function run() {
			phpayroll.printable.open_preview({
				title: opts.title,
				load: function (state, done) {
					frappe.call({
						method: opts.method,
						args: Object.assign({}, opts.args || {}, {
							fields_only: state.fields_only ? 1 : 0,
						}),
						freeze: opts.freeze !== false,
						freeze_message: opts.freeze_message || __("Preparing printable form..."),
						callback: function (r) {
							if (r.exc) {
								done(null);
								return;
							}
							if (!(r.message && (r.message.file_url || r.message.data_uri))) {
								frappe.msgprint({
									title: __("Error"),
									message: __("Could not generate the filled PDF."),
									indicator: "red",
								});
								done(null);
								return;
							}
							done(r.message);
						},
						error: function () {
							done(null);
						},
					});
				},
			});
		}
		if (phpayroll.printable.open_preview) {
			run();
		}
	};
})();
