// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.provide("phpayroll.reports");

(function () {
	const PH_REPORTS = {
		"BIR 1601-C": 1,
		"BIR 1604-C": 1,
		"SSS R-3": 1,
		"PhilHealth RF-1": 1,
		"Pag-IBIG MCRF": 1,
	};

	function is_missing(name) {
		return name == null || name === "" || name === "undefined";
	}

	function patch_generate_route() {
		if (!frappe.utils || !frappe.utils.generate_route || frappe.utils.generate_route.__phpayroll) {
			return;
		}
		const orig = frappe.utils.generate_route;
		frappe.utils.generate_route = function (item) {
			if (item && String(item.type || "").toLowerCase() === "report") {
				if (is_missing(item.name)) {
					item.name = item.link_to || item.label || item.report_name;
				}
				if (item.name && PH_REPORTS[item.name]) {
					item.is_query_report = 1;
				}
				if (is_missing(item.name)) {
					return "/desk";
				}
			}
			return orig.call(this, item);
		};
		frappe.utils.generate_route.__phpayroll = true;
	}

	function patch_with_doctype() {
		if (!frappe.model || !frappe.model.with_doctype || frappe.model.with_doctype.__phpayroll) {
			return;
		}
		const orig = frappe.model.with_doctype;
		frappe.model.with_doctype = function (doctype, callback, async) {
			if (is_missing(doctype)) {
				callback && callback();
				return Promise.resolve();
			}
			return orig.call(this, doctype, callback, async);
		};
		frappe.model.with_doctype.__phpayroll = true;
	}

	function patch_query_report() {
		if (!frappe.views || !frappe.views.QueryReport) {
			return;
		}
		const proto = frappe.views.QueryReport.prototype;
		if (proto.__phpayroll_patched) {
			return;
		}
		proto.__phpayroll_patched = true;

		const orig_load = proto.load;
		proto.load = function () {
			if (is_missing(frappe.get_route()[1])) {
				this.toggle_nothing_to_show(true);
				return;
			}
			return orig_load.apply(this, arguments);
		};

		proto.get_report_doc = function () {
			if (is_missing(this.report_name)) {
				return Promise.resolve();
			}
			return frappe.model
				.with_doc("Report", this.report_name)
				.then((doc) => {
					this.report_doc = doc;
				})
				.then(() => {
					const dt = this.report_doc && this.report_doc.ref_doctype;
					if (is_missing(dt)) {
						return;
					}
					return frappe.model.with_doctype(dt);
				});
		};
	}

	function strip_broken_report_hrefs() {
		$(".body-sidebar a.item-anchor[href*='query-report/undefined']").removeAttr("href");
	}

	patch_generate_route();
	patch_with_doctype();
	$(document).on("app_ready", function () {
		patch_generate_route();
		patch_with_doctype();
		patch_query_report();
	});
	$(document).on("sidebar_setup", strip_broken_report_hrefs);
})();
