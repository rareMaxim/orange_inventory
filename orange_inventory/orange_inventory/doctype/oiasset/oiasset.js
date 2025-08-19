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
	// Фільтр для поля "Відповідальний співробітник" на основі підприємства
	frm.set_query("responsible_employee", function () {
		return {
			filters: {
				organization: frm.doc.current_owner,
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
		responsible_employee_filter(frm);
		calculate_total_amount(frm);
		// Показуємо кнопку тільки якщо актив "груповий" і знаходиться на складі
		if (frm.doc.quantity > 1 && !frm.is_new()) {
			frm.add_custom_button(__("Розділити Актив"), function () {
				open_split_asset_dialog(frm);
			}).addClass("btn-primary");
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
	current_owner: function (frm) {
		responsible_employee_filter(frm);
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
