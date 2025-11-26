frappe.listview_settings["oiAsset"] = {
	hide_name_column: true, // hide the last column which shows the `name`
	hide_name_filter: true, // hide the default filter field for the name column
	add_fields: ["inventory_date", "inventory_status", "quantity", "status"],

	get_indicator: function (doc) {
		// Стандартний індикатор статусу активу
		const status_colors = {
			"Очікує прийняття": "orange",
			"На складі": "green",
			"В експлуатації": "blue",
			Передано: "yellow",
			Списується: "purple",
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

	// Масове додавання активів до акту списання
	onload: function (listview) {
		listview.page.add_action_item(__("Додати до акту списання"), function () {
			const selected_items = listview.get_checked_items();

			if (selected_items.length === 0) {
				frappe.msgprint(__("Оберіть хоча б один актив"));
				return;
			}

			// Фільтруємо активи, які можна списати
			const valid_assets = selected_items.filter(
				(doc) =>
					doc.quantity > 0 && doc.status !== "Списано" && doc.status !== "Списується"
			);

			if (valid_assets.length === 0) {
				frappe.msgprint(
					__("Обрані активи не можна додати до списання (вже списані або кількість = 0)")
				);
				return;
			}

			if (valid_assets.length < selected_items.length) {
				frappe.msgprint(
					__(
						"Деякі активи не можна додати до списання. Буде додано {0} з {1} обраних активів.",
						[valid_assets.length, selected_items.length]
					)
				);
			}

			// Діалог для вибору акту списання та причини
			let d = new frappe.ui.Dialog({
				title: __("Додати активи до акту списання"),
				fields: [
					{
						label: __("Кількість активів"),
						fieldname: "info",
						fieldtype: "HTML",
						options: `<div style="padding: 10px; background-color: #f0f4f7; border-radius: 4px; margin-bottom: 15px;">
							<strong>Обрано активів:</strong> ${valid_assets.length}
						</div>`,
					},
					{
						label: __("Оберіть акт списання"),
						fieldname: "decommissioning_act",
						fieldtype: "Link",
						options: "oiDecommissioningAct",
						reqd: 1,
						get_query: function () {
							return {
								filters: {
									docstatus: 0, // Тільки чернетки
								},
							};
						},
						description: __("Оберіть існуючий акт списання"),
					},
					{
						label: __("Причина списання"),
						fieldname: "reason",
						fieldtype: "Small Text",
						default: "Вихід з ладу у зв'язку з інтенсивною експлуатацією",
						reqd: 1,
					},
				],
				primary_action_label: __("Додати"),
				primary_action(values) {
					frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.add_multiple_assets_to_decommissioning_act",
						args: {
							asset_names: valid_assets.map((a) => a.name),
							decommissioning_act: values.decommissioning_act,
							reason: values.reason,
						},
						freeze: true,
						freeze_message: __("Додаємо активи до акту списання..."),
						callback: function (r) {
							if (!r.exc) {
								frappe.show_alert({
									message: __("Активи успішно додано до акту списання"),
									indicator: "green",
								});
								d.hide();
								listview.refresh();

								// Питаємо користувача, чи хоче він відкрити акт списання
								frappe.confirm(__("Відкрити акт списання?"), function () {
									frappe.set_route("Form", "oiDecommissioningAct", r.message);
								});
							}
						},
					});
				},
			});
			d.show();
		});
	},
};
