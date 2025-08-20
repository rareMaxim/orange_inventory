frappe.ui.form.on("oiReceiptOrder", {
	refresh(frm) {
		run_all_validations_and_update_intro(frm);
		update_dashboard(frm);
	},
	items_remove(frm) {
		update_dashboard(frm);
	},
});

frappe.ui.form.on("oiReceiptOrderItem", {
	qty(frm, cdt, cdn) {
		calculate_row_total(frm, cdt, cdn); // Використовуємо глобальну функцію
		run_all_validations_and_update_intro(frm, cdt, cdn);
		update_dashboard(frm);
	},
	rate(frm, cdt, cdn) {
		calculate_row_total(frm, cdt, cdn); // Використовуємо глобальну функцію
		update_dashboard(frm);
	},
	asset_type(frm) {
		// Затримка потрібна, щоб Frappe встиг виконати "fetch" для нового поля
		setTimeout(() => update_dashboard(frm), 200);
	},
	items_add(frm, cdt, cdn) {
		let items = frm.doc.items;
		if (items.length > 1) {
			let previous_asset_type = items[items.length - 2].asset_type;
			let new_row = items[items.length - 1];
			new_row.asset_type = previous_asset_type;
			frm.refresh_field("items");
		}
	},
	asset_name(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.asset_name) {
			let sanitized_name = row.asset_name.replace(/\s+/g, " ").trim();
			frappe.model.set_value(cdt, cdn, "asset_name", sanitized_name, true);
		}
	},
	serial_numbers(frm, cdt, cdn) {
		run_all_validations_and_update_intro(frm, cdt, cdn);
	},
});
let calculate_row_total = function (frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let total = flt(row.qty) * flt(row.rate);
	frappe.model.set_value(cdt, cdn, "total_amount", total);
	frm.refresh_field("items");
};
let calculate_total_amount = function (frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let total = flt(row.qty) * flt(row.rate);
	frappe.model.set_value(cdt, cdn, "total_amount", total);
	frm.refresh_field("items");
};
function run_all_validations_and_update_intro(frm) {
	let errors = [];
	if (frm.doc.items) {
		frm.doc.items.forEach((item, index) => {
			if (!item.asset_name) return;
			const { count, expected, has_duplicates } = parse_serials(
				item.serial_numbers,
				item.qty
			);

			if (item.qty > 1 && count > 0 && count !== expected) {
				errors.push(
					`<b>${item.asset_name} (Рядок ${
						index + 1
					})</b>: Кількість серійних номерів (${count}) не співпадає з кількістю (${expected}).`
				);
			}
			if (has_duplicates) {
				errors.push(
					`<b>${item.asset_name} (Рядок ${
						index + 1
					})</b>: Знайдено дублікати в серійних номерах.`
				);
			}
		});
	}

	if (errors.length > 0) {
		const error_html = errors.join("<br>");
		frm.set_intro(
			`<div class="frappe-indicator-red"><b>Документ містить помилки:</b><br>${error_html}</div>`,
			"red"
		);
	} else {
		frm.set_intro("Всі перевірки пройдено.", "green");
	}
	return errors;
}
// -- ЛОГІКА ВАЛІДАЦІЇ СЕРІЙНИХ НОМЕРІВ --

/**
 * Розбирає рядок з серійними номерами, рахує їх та перевіряє на дублікати.
 * Враховує коми та символи нового рядка як роздільники.
 * @param {string} serials_string - Рядок для аналізу.
 * @param {number} expected_qty - Очікувана кількість.
 * @returns {object} - Об'єкт з результатами аналізу.
 */
function parse_serials(serials_string, expected_qty) {
	if (!serials_string) {
		return { count: 0, expected: expected_qty, has_duplicates: false };
	}
	const serials_list = serials_string
		.split(/[\n,]+/)
		.map((s) => s.trim())
		.filter((s) => s);
	const unique_serials = new Set(serials_list);
	return {
		count: serials_list.length,
		expected: expected_qty,
		has_duplicates: serials_list.length !== unique_serials.size,
	};
}

let update_dashboard = function (frm) {
	if (!frm.doc.items || frm.doc.items.length === 0) {
		frm.fields_dict.dashboard.html("");
		return;
	}

	let total_qty = 0;
	let total_amount = 0;
	let stats_by_type = {};

	frm.doc.items.forEach((item) => {
		if (item.asset_name) {
			total_qty += item.qty;
			total_amount += item.total_amount;

			let type_name = item.asset_type || "Не вказано";

			if (!stats_by_type[type_name]) {
				stats_by_type[type_name] = {
					qty: 0,
					amount: 0,
					asset_type_name: item.asset_type_name || "Не вказано",
				};
			}
			stats_by_type[type_name].qty += item.qty;
			stats_by_type[type_name].amount += item.total_amount;
		}
	});

	let html = `
        <div style="padding: 10px;">
            <h4>Загальні показники</h4>
            <div class="row">
                <div class="col-md-6">
                    <div class="card" style="margin-bottom: 10px;">
                        <div class="card-body">
                            <h5 class="card-title">${format_number(total_qty)} од.</h5>
                            <p class="card-text text-muted">Всього одиниць</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card" style="margin-bottom: 10px;">
                        <div class="card-body">
                            <h5 class="card-title">${format_currency(total_amount)}</h5>
                            <p class="card-text text-muted">Загальна вартість</p>
                        </div>
                    </div>
                </div>
            </div>
            <hr>
            <h4>В розрізі типів</h4>
            <table class="table table-bordered table-sm">
                <thead>
                    <tr>
                        <th>Тип активу</th>
                        <th class="text-right">Кількість</th>
                        <th class="text-right">Сума</th>
                    </tr>
                </thead>
                <tbody>
    `;

	for (let type_name in stats_by_type) {
		html += `
                    <tr>
                        <td>${stats_by_type[type_name].asset_type_name}</td>
                        <td class="text-right">${format_number(stats_by_type[type_name].qty)}</td>
                        <td class="text-right">${format_currency(
							stats_by_type[type_name].amount
						)}</td>
                    </tr>
        `;
	}

	html += `
                </tbody>
            </table>
        </div>
    `;

	frm.fields_dict.dashboard.html(html);
};
