frappe.listview_settings["oiAsset"] = {
	hide_name_column: true, // hide the last column which shows the `name`
	hide_name_filter: true, // hide the default filter field for the name column
	add_fields: ["inventory_date", "inventory_status"],

	get_indicator: function (doc) {
		// Стандартний індикатор статусу активу
		const status_colors = {
			"Очікує прийняття": "orange",
			"На складі": "green",
			"В експлуатації": "blue",
			Передано: "yellow",
			Списано: "red",
		};

		return [doc.status, status_colors[doc.status] || "gray", "status,=," + doc.status];
	},

	formatters: {
		inventory_status: function (value) {
			if (!value) {
				return '<span style="color: gray;">Немає даних</span>';
			}

			// Визначаємо колір на основі тексту статусу
			let color = "gray";
			if (value.includes("✓")) {
				color = "#5cb85c"; // зелений
			} else if (value.includes("3 міс")) {
				color = "#5bc0de"; // блакитний
			} else if (value.includes("6 міс")) {
				color = "#ff9800"; // жовто-помаранчевий
			} else if (value.includes("9 міс")) {
				color = "#f0ad4e"; // помаранчевий
			} else if (value.includes("12 міс")) {
				color = "#d9534f"; // червоний
			}

			return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		},
	},
};
