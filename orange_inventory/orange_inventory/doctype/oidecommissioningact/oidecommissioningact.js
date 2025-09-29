// Copyright (c) 2025, Maxim Sysoev
// For license information, please see license.txt

// === helpers ===
function recalc_row_and_parent(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);

	// поля згідно твоєї таблиці: count, cost, total
	const count = Math.max(0, flt(row.count));
	const cost = flt(row.unit_price);
	const total = cost * count;

	// попередження, якщо перевищили доступну кількість
	if (row.avaible_count && count > flt(row.avaible_count)) {
		frappe.show_alert({
			message: __("Кількість перевищує доступну (доступно: {0})", [row.avaible_count]),
			indicator: "orange",
		});
	}

	frappe.model.set_value(cdt, cdn, "total", total);

	// Перерахунок сум у батьківському документі
	if (frm?.doc?.items) {
		let sum = 0.0;
		(frm.doc.items || []).forEach((it) => (sum += flt(it.total)));
		if (frm.fields_dict["total_amount"]) {
			frm.set_value("total_amount", sum);
		}
		frm.refresh_field("items");
	}
}

// універсальний підсумок
function recompute_total_parent(frm) {
	if (!frm.fields_dict["total_amount"]) return;
	let sum = 0.0;
	(frm.doc.items || []).forEach((it) => (sum += flt(it.total)));
	frm.set_value("total_amount", sum);
}

// === child events (реєструємо в скрипті батьківського доктайпу) ===
frappe.ui.form.on("oiDecommissioningItem", {
	// при введенні кількості — перерахунок суми
	count(frm, cdt, cdn) {
		recalc_row_and_parent(frm, cdt, cdn);
	},

	// якщо змінилась ціна (хоча у тебе вона fetch_from=asset.cost) — теж перерахунок
	cost(frm, cdt, cdn) {
		recalc_row_and_parent(frm, cdt, cdn);
	},

	// після вибору активу (cost/inventory_no підтягнуться з fetch_from) — перерахуємо total
	asset(frm, cdt, cdn) {
		recalc_row_and_parent(frm, cdt, cdn);
	},

	// зробити колонку total readonly у гріді
	items_add(frm) {
		const fld = frm.fields_dict.items?.grid?.get_field("total");
		if (fld) fld.df.read_only = 1;
	},
});

// === parent doctype ===
frappe.ui.form.on("oiDecommissioningAct", {
	refresh(frm) {
		// кнопки листування
		if (frm.doc.docstatus !== 2 && !frm.doc.correspondence) {
			frm.add_custom_button(__("Створити службовий лист на списання"), async () => {
				if (frm.is_dirty()) await frm.save();
				frappe.call({
					method: "orange_inventory.orange_inventory.doctype.oidecommissioningact.oidecommissioningact.create_correspondence_for_act",
					args: { act_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Готуємо службовий лист..."),
					callback: (r) => {
						if (r?.message) {
							frm.set_value("correspondence", r.message);
							frm.save().then(() =>
								frappe.set_route("Form", "oiCorrespondence", r.message)
							);
						}
					},
				});
			});
		}

		if (frm.doc.correspondence) {
			frm.add_custom_button(__("Відкрити службовий лист"), () => {
				frappe.set_route("Form", "oiCorrespondence", frm.doc.correspondence);
			});
		}
		recompute_total_parent(frm);
	},

	// коли грід перерендерився / щось видалили — оновимо підсумок
	items_on_form_rendered(frm) {
		recompute_total_parent(frm);
	},
	items_remove(frm) {
		recompute_total_parent(frm);
	},
});
