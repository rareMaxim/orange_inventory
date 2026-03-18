import frappe


def create_doctype():
	if not frappe.db.exists("DocType", "oi Network Discovery Settings"):
		doc = frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "oi Network Discovery Settings",
				"module": "Orange Inventory",
				"custom": 1,
				"issingle": 1,
				"fields": [
					{
						"fieldname": "target_subnets",
						"fieldtype": "Small Text",
						"label": "Target Subnets",
						"reqd": 1,
					},
					{
						"fieldname": "community_strings",
						"fieldtype": "Small Text",
						"label": "SNMP Community Strings",
						"reqd": 1,
					},
					{
						"fieldname": "assigned_agent",
						"fieldtype": "Link",
						"options": "oiAgent",
						"label": "Assigned Agent",
					},
					{
						"fieldname": "schedule",
						"fieldtype": "Select",
						"options": "Manual\nDaily\nWeekly",
						"label": "Schedule",
						"default": "Manual",
					},
				],
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		print("DocType created successfully")
	else:
		print("DocType already exists")


if __name__ == "__main__":
	create_doctype()
