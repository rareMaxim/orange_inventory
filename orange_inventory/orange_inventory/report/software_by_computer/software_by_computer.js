// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.query_reports["Software by Computer"] = {
	filters: [
		{
			fieldname: "agent",
			label: __("Комп'ютер"),
			fieldtype: "Link",
			options: "oiAgent",
		},
		{
			fieldname: "software_name",
			label: __("Назва програми"),
			fieldtype: "Data",
		},
		{
			fieldname: "compliance_status",
			label: __("Статус відповідності"),
			fieldtype: "Select",
			options: "\nДозволено\nЗаборонено\nНе в каталозі\nНе перевірено",
		},
		{
			fieldname: "needs_update",
			label: __("Потребує оновлення"),
			fieldtype: "Check",
		},
	],
};
