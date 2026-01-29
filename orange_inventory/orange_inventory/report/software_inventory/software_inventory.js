// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.query_reports["Software Inventory"] = {
	filters: [
		{
			fieldname: "software_name",
			label: __("Назва програми"),
			fieldtype: "Data",
		},
		{
			fieldname: "publisher",
			label: __("Видавець"),
			fieldtype: "Data",
		},
		{
			fieldname: "compliance_status",
			label: __("Статус відповідності"),
			fieldtype: "Select",
			options: "\nДозволено\nЗаборонено\nНе в каталозі\nНе перевірено",
		},
	],
};
