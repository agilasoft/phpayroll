import frappe


def execute():
	"""Remove HR and HR & Payroll workspaces from the database."""
	workspace_names = ["HR", "HR & Payroll", "hr_payroll", "hr-&--payroll"]
	for name in workspace_names:
		if frappe.db.exists("Workspace", name):
			# Delete sidebar items linking to this workspace first (bypasses Workspace Sidebar doc lookup)
			frappe.db.delete("Workspace Sidebar Item", {"link_to": name, "link_type": "Workspace"})
			frappe.db.delete("Workspace", name)
	frappe.db.commit()
