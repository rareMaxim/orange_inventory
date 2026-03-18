import frappe


def run():
	agent = frappe.db.get_list("oiAgent", limit=1)
	if agent:
		frappe.db.sql(
			"UPDATE `tabSingles` SET value=%s WHERE doctype='oi Network Discovery Settings' AND field='assigned_agent'",
			(agent[0].name,),
		)
		frappe.db.commit()
		print("Assigned to:", agent[0].name)


run()
