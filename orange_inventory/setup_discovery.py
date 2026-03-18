import frappe


def setup():
	frappe.db.sql("DELETE FROM `tabSingles` WHERE doctype='oi Network Discovery Settings'")

	# Use the active agent on this system
	agent_name = "frappe-develop-b24216ed"

	settings = {
		"target_subnets": "192.168.33.1/32\n192.168.33.170/32",
		"community_strings": "public",
		"schedule": "Manual",
		"assigned_agent": agent_name,
	}

	for k, v in settings.items():
		frappe.db.sql(
			"INSERT INTO `tabSingles` (doctype, field, value) VALUES (%s, %s, %s)",
			("oi Network Discovery Settings", k, v),
		)

	frappe.db.commit()
	print("Settings configured.")


if __name__ == "__main__":
	setup()
