function phpayroll_report_buttons(report, opts) {
	report.page.add_inner_button(
		__("Download File"),
		function () {
			const filters = report.get_values();
			frappe.call({
				method: opts.dat_method,
				args: { filters: filters },
				callback: function (r) {
					if (!r.message) return;
					const blob = new Blob([r.message], { type: "text/plain" });
					const url = window.URL.createObjectURL(blob);
					const a = document.createElement("a");
					a.href = url;
					a.download = typeof opts.dat_name === "function" ? opts.dat_name(filters) : opts.dat_name;
					document.body.appendChild(a);
					a.click();
					document.body.removeChild(a);
					window.URL.revokeObjectURL(url);
				},
			});
		},
		__("Download")
	);

	report.page.add_inner_button(
		opts.pdf_label || __("Printable PDF"),
		function () {
			const filters = report.get_values();
			function open() {
				phpayroll.printable.preview_form({
					title: opts.pdf_label || __("Printable Form"),
					method: "phpayroll.ph_payroll.statutory_reports.pdf_forms.export_printable_form",
					args: { filters: filters, form: opts.form },
					freeze: true,
					freeze_message: __("Preparing printable form..."),
				});
			}
			if (window.phpayroll && phpayroll.printable && phpayroll.printable.preview_form) {
				open();
			} else {
				frappe.require("/assets/phpayroll/js/printable_pdf_preview.js", open);
			}
		},
		__("Download")
	);
}
