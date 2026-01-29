# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "hostname",
			"label": "Комп'ютер",
			"fieldtype": "Link",
			"options": "oiAgent",
			"width": 180,
		},
		{
			"fieldname": "software_name",
			"label": "Програма",
			"fieldtype": "Data",
			"width": 280,
		},
		{
			"fieldname": "version",
			"label": "Версія",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "publisher",
			"label": "Видавець",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "compliance_status",
			"label": "Статус",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "needs_update",
			"label": "Оновити",
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "install_date",
			"label": "Дата встановлення",
			"fieldtype": "Date",
			"width": 120,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters:
		if filters.get("agent"):
			conditions.append("sw.agent = %(agent)s")
			values["agent"] = filters.get("agent")

		if filters.get("compliance_status"):
			conditions.append("sw.compliance_status = %(compliance_status)s")
			values["compliance_status"] = filters.get("compliance_status")

		if filters.get("needs_update"):
			conditions.append("sw.needs_update = 1")

		if filters.get("software_name"):
			conditions.append("sw.software_name LIKE %(software_name)s")
			values["software_name"] = f"%{filters.get('software_name')}%"

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	data = frappe.db.sql(
		f"""
		SELECT
			ag.hostname,
			sw.agent,
			sw.software_name,
			sw.version,
			sw.publisher,
			sw.compliance_status,
			sw.needs_update,
			sw.install_date
		FROM `taboiAgentSoftware` sw
		LEFT JOIN `taboiAgent` ag ON sw.agent = ag.name
		{where_clause}
		ORDER BY ag.hostname, sw.software_name
	""",
		values,
		as_dict=True,
	)

	return data
