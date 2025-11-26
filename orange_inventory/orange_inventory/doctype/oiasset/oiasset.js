// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

/**
 * Функція для розрахунку загальної суми активу.
 */

let manufacturer_filter = function (frm) {
	// Фільтр для поля "Виробник" на основі вибраної моделі
	frm.set_query("hardware_model", function () {
		return {
			filters: {
				manufacturer: frm.doc.manufacturer,
			},
		};
	});
};
let responsible_employee_filter = function (frm) {
	// Фільтр для поля "Виробник" на основі вибраної моделі
	frm.set_query("responsible_employee", function () {
		return {
			filters: {
				// status: frm.doc.manufacturer,
			},
		};
	});
};
let calculate_total_amount = function (frm) {
	let cost = flt(frm.doc.cost);
	let qty = flt(frm.doc.quantity);
	let total_amount = cost * qty;
	frm.doc.total = total_amount;
	frm.refresh_field("total");
};

frappe.ui.form.on("oiAsset", {
	refresh(frm) {
		manufacturer_filter(frm);
		calculate_total_amount(frm);
		update_inventory_status_display(frm);

		// Показуємо кнопку тільки якщо актив "груповий" і знаходиться на складі
		if (frm.doc.quantity > 1 && !frm.is_new()) {
			frm.add_custom_button(__("Розділити Актив"), function () {
				open_split_asset_dialog(frm);
			}).addClass("btn-primary");
		}

		// Кнопка для проведення інвентаризації
		if (!frm.is_new()) {
			frm.add_custom_button(__("Провести Інвентаризацію"), function () {
				conduct_inventory(frm);
			});
		}

		// Кнопка для додавання до акту списання або відкриття існуючого акту
		if (!frm.is_new() && frm.doc.quantity > 0 && frm.doc.status !== "Списано") {
			// Перевіряємо, чи актив вже в акті списання
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.find_decommissioning_act_for_asset",
				args: {
					asset_name: frm.doc.name,
				},
				callback: function (r) {
					if (r.message) {
						// Актив вже в акті списання - показуємо кнопку для відкриття акту
						frm.add_custom_button(__("Відкрити акт списання"), function () {
							frappe.set_route("Form", "oiDecommissioningAct", r.message);
						});
					} else {
						// Актив ще не в акті - показуємо кнопку для додавання
						frm.add_custom_button(__("Додати до списання"), function () {
							add_to_decommissioning_act(frm);
						});
					}
				},
			});
		}

		// Показуємо інформацію про батьківський актив, якщо компонент встановлено
		if (frm.doc.parent_asset) {
			frappe.db.get_value("oiAsset", frm.doc.parent_asset, "asset_name").then((r) => {
				if (r.message && r.message.asset_name) {
					frm.dashboard.add_comment(
						__("Цей актив встановлено в: {0}", [
							`<a href="/app/oiasset/${frm.doc.parent_asset}">${r.message.asset_name}</a>`,
						]),
						"blue",
						true
					);
				}
			});
		}

		// Якщо це мережевий пристрій, показуємо вкладку "Мережа" та завантажуємо порти
		if (frm.doc.hardware_model) {
			frappe.db
				.get_value("oiHardwareModel", frm.doc.hardware_model, "is_network_device")
				.then((r) => {
					if (r.message && r.message.is_network_device) {
						frm.toggle_display("network_ports_dashboard", true);
						render_network_ports(frm);
					} else {
						frm.toggle_display("network_ports_dashboard", false);
					}
				});
		}
	},
	cost(frm) {
		calculate_total_amount(frm);
	},
	qty(frm) {
		calculate_total_amount(frm);
	},
	manufacturer: function (frm) {
		manufacturer_filter(frm);
	},
});

// Обробники для child table "components"
frappe.ui.form.on("oiAssetComponent", {
	component_asset: function (_frm, cdt, cdn) {
		// Оновлюємо дані про компонент після його вибору
		let row = locals[cdt][cdn];
		if (row.component_asset) {
			frappe.db.get_doc("oiAsset", row.component_asset).then((doc) => {
				frappe.model.set_value(cdt, cdn, "asset_name", doc.asset_name);
				frappe.model.set_value(cdt, cdn, "serial_no", doc.serial_no);
			});
		}
	},
});

let open_split_asset_dialog = function (frm) {
	let d = new frappe.ui.Dialog({
		title: __("Розділення Активу: " + frm.doc.asset_name),
		fields: [
			{
				label: "Загальна кількість",
				fieldname: "total_quantity_info",
				fieldtype: "HTML",
				options: `<div style="padding: 10px; background-color: #f0f4f7; border-radius: 4px; margin-bottom: 10px;">
					<strong>Поточна кількість:</strong> ${frm.doc.quantity} шт.
				</div>`,
			},
			{
				label: "Кількість для відокремлення",
				fieldname: "quantity_to_split",
				fieldtype: "Int",
				reqd: 1,
				default: 1,
				description: __(
					"Вкажіть скільки одиниць потрібно відокремити від основної позиції (від 1 до {0})",
					[frm.doc.quantity - 1]
				),
			},
			{
				fieldtype: "Column Break",
			},
			{
				label: "Серійні номери для відокремлених одиниць",
				fieldname: "serial_numbers",
				fieldtype: "Small Text",
				reqd: 0,
				description: __(
					"Введіть серійні номери для відокремлених одиниць, кожен з нового рядка або через кому (необов'язково)."
				),
			},
		],
		primary_action_label: __("Розділити"),
		primary_action(values) {
			// Валідація кількості для відокремлення
			const quantity_to_split = parseInt(values.quantity_to_split);
			if (quantity_to_split < 1 || quantity_to_split >= frm.doc.quantity) {
				frappe.msgprint(
					__("Кількість для відокремлення повинна бути від 1 до {0}", [
						frm.doc.quantity - 1,
					])
				);
				return;
			}

			// "Очищаємо" список серійних номерів від зайвих пробілів та пустих рядків
			let serials = [];
			if (values.serial_numbers && values.serial_numbers.trim()) {
				serials = values.serial_numbers
					.replace(/\n/g, ",") // замінюємо нові рядки на коми
					.split(",")
					.map((s) => s.trim())
					.filter((s) => s); // видаляємо пусті елементи

				// Перевіряємо тільки якщо були введені серійні номери
				if (serials.length !== quantity_to_split) {
					frappe.msgprint(
						__(
							"Кількість введених серійних номерів ({0}) не співпадає з кількістю для відокремлення ({1}).",
							[serials.length, quantity_to_split]
						)
					);
					return;
				}
			}

			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.split_asset_partial",
				args: {
					source_asset_name: frm.doc.name,
					quantity_to_split: quantity_to_split,
					serial_numbers: serials,
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Актив успішно розділено"),
							indicator: "green",
						});
						frm.reload_doc();
						d.hide();
					}
				},
			});
		},
	});
	d.show();
};

function render_network_ports(frm) {
	frappe.call({
		method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.get_network_ports_with_details",
		args: {
			asset_name: frm.doc.name,
		},
		callback: function (r) {
			if (r.message) {
				let html = `
                    <div class="table-responsive">
                        <table class="table table-bordered table-hover">
                            <thead class="thead-light">
                                <tr>
                                    <th style="width: 20%;">Порт</th>
                                    <th style="width: 20%;">Тип</th>
                                    <th>З'єднано з</th>
                                    <th style="width: 15%;" class="text-right">Дії</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
				if (r.message.length === 0) {
					html += `<tr><td colspan="4" class="text-center text-muted">Для цієї моделі не створено мережевих портів.</td></tr>`;
				} else {
					r.message.forEach((port) => {
						let connection_status_html = "";
						if (port.is_wan_connection) {
							connection_status_html = `<span class="badge badge-primary" style="font-size: 14px;">🌐 Підключення до Інтернету</span>`;
						} else if (port.connection && port.connected_asset_name) {
							// ВИКОРИСТОВУЄМО НОВІ ПОЛЯ: connected_asset_name та connected_port_name
							connection_status_html = `
                                <div>
									<a href="/app/oiasset/${port.connected_asset}">${port.connected_asset_name}</a>
								</div>
                                <small class="text-muted">Порт:
									<a href="/app/oinetworkport/${port.connection}">${port.connected_port_name || port.connection}</a>
								</small>
                            `;
						} else {
							connection_status_html = `<span class="text-muted">Не підключено</span>`;
						}
						html += `
                        <tr>
                            <td><strong>${port.port_name}</strong></td>
                            <td>${port.port_type}</td>
                            <td>${connection_status_html}</td>
                            <td class="text-right">
                                <a href="/app/oinetworkport/${port.name}" class="btn btn-sm btn-default">
                                    <i class="fa fa-edit"></i> Редагувати
                                </a>
                            </td>
                        </tr>
                    `;
					});
				}
				html += `</tbody></table></div>`;
				frm.fields_dict.network_ports_dashboard.html(html);
			}
		},
	});
}

// Функція для проведення інвентаризації
let conduct_inventory = function (frm) {
	let d = new frappe.ui.Dialog({
		title: __("Провести Інвентаризацію"),
		fields: [
			{
				label: "Дата інвентаризації",
				fieldname: "inventory_date",
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				label: "Місцезнаходження",
				fieldname: "location",
				fieldtype: "Link",
				options: "oiLocation",
				default: frm.doc.location,
				description: __("Оберіть місцезнаходження активу (необов'язково)"),
			},
		],
		primary_action_label: __("Провести"),
		primary_action(values) {
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.set_inventory_date",
				args: {
					asset_name: frm.doc.name,
					inventory_date: values.inventory_date,
					location: values.location,
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Інвентаризація проведена успішно"),
							indicator: "green",
						});
						frm.reload_doc();
						d.hide();
					}
				},
			});
		},
	});
	d.show();
};

// Функція для оновлення відображення статусу інвентаризації
let update_inventory_status_display = function (frm) {
	if (!frm.doc.inventory_date) {
		return;
	}

	frappe.call({
		method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.get_inventory_status",
		args: {
			asset_name: frm.doc.name,
		},
		callback: function (r) {
			if (r.message && r.message.status) {
				let status = r.message.status;
				let color = r.message.color;

				frm.set_df_property(
					"inventory_date",
					"description",
					`<span style="color: ${color}; font-weight: bold;">${status}</span>`
				);
			}
		},
	});
};

// Функція для додавання активу до акту списання
let add_to_decommissioning_act = function (frm) {
	let d = new frappe.ui.Dialog({
		title: __("Додати до акту списання"),
		fields: [
			{
				label: "Актив",
				fieldname: "asset_info",
				fieldtype: "HTML",
				options: `<div style="padding: 10px; background-color: #f0f4f7; border-radius: 4px; margin-bottom: 15px;">
					<strong>Актив:</strong> ${frm.doc.asset_name}<br>
					<strong>Інвентарний номер:</strong> ${frm.doc.inventory_no || "—"}<br>
					<strong>Серійний номер:</strong> ${frm.doc.serial_no || "—"}<br>
					<strong>Доступна кількість:</strong> ${frm.doc.quantity} шт.<br>
					<strong>Вартість за одиницю:</strong> ${format_currency(frm.doc.cost, "UAH")}
				</div>`,
			},
			{
				label: "Оберіть акт списання",
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
				description: __(
					"Оберіть існуючий акт списання або залишіть порожнім для створення нового"
				),
			},
			{
				fieldtype: "Column Break",
			},
			{
				label: "Кількість для списання",
				fieldname: "quantity",
				fieldtype: "Float",
				reqd: 1,
				default: frm.doc.quantity,
				description: __("Вкажіть кількість одиниць для списання (максимум: {0})", [
					frm.doc.quantity,
				]),
			},
			{
				label: "Причина списання",
				fieldname: "reason",
				fieldtype: "Small Text",
				default: "Вихід з ладу у зв'язку з інтенсивною експлуатацією",
				reqd: 1,
			},
		],
		primary_action_label: __("Додати"),
		primary_action(values) {
			// Валідація кількості
			const qty = parseFloat(values.quantity);
			if (qty <= 0 || qty > frm.doc.quantity) {
				frappe.msgprint(__("Кількість повинна бути від 0 до {0}", [frm.doc.quantity]));
				return;
			}

			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.add_asset_to_decommissioning_act",
				args: {
					asset_name: frm.doc.name,
					decommissioning_act: values.decommissioning_act,
					quantity: qty,
					reason: values.reason,
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Актив додано до акту списання"),
							indicator: "green",
						});
						d.hide();

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
};
