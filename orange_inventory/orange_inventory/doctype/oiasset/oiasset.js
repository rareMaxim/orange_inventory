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
		// Показуємо кнопку тільки якщо актив "груповий" і знаходиться на складі
		if (frm.doc.quantity > 1 && !frm.is_new()) {
			frm.add_custom_button(__("Розділити Актив"), function () {
				open_split_asset_dialog(frm);
			}).addClass("btn-primary");
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

let open_split_asset_dialog = function (frm) {
	let d = new frappe.ui.Dialog({
		title: __("Розділення Активу: " + frm.doc.asset_name),
		fields: [
			{
				label: "Серійні номери",
				fieldname: "serial_numbers",
				fieldtype: "Small Text",
				reqd: 1,
				description: __(
					"Введіть  <b>{0}</b> серійних номерів, кожен з нового рядка або через кому.",
					[frm.doc.quantity]
				),
			},
		],
		primary_action_label: __("Розділити"),
		primary_action(values) {
			// "Очищаємо" список серійних номерів від зайвих пробілів та пустих рядків
			const serials = values.serial_numbers
				.replace(/\n/g, ",") // замінюємо нові рядки на коми
				.split(",")
				.map((s) => s.trim())
				.filter((s) => s); // видаляємо пусті елементи

			if (serials.length !== frm.doc.quantity) {
				frappe.msgprint(
					__(
						"Кількість введених серійних номерів ({0}) не співпадає з кількістю активу ({1}).",
						[serials.length, frm.doc.quantity]
					)
				);
				return;
			}

			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oiasset.oiasset.split_asset",
				args: {
					source_asset_name: frm.doc.name,
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
