frappe.ui.form.on('oiReceiptOrder', {
    refresh(frm) {
        update_dashboard(frm);
    },
    items_remove(frm) {
        update_dashboard(frm);
    }
});

frappe.ui.form.on('oiReceiptOrderItem', {
    qty(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn); // Використовуємо глобальну функцію
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
            frm.refresh_field('items');
        }
    },
    asset_name(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.asset_name) {
            let sanitized_name = row.asset_name.replace(/\s+/g, ' ').trim();
            frappe.model.set_value(cdt, cdn, 'asset_name', sanitized_name, true);
        }
    }
});

let calculate_total_amount = function (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let total = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'total_amount', total);
    frm.refresh_field('items');
};

let update_dashboard = function (frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frm.fields_dict.dashboard.html('');
        return;
    }

    let total_qty = 0;
    let total_amount = 0;
    let stats_by_type = {};

    frm.doc.items.forEach(item => {
        if (item.asset_name) {
            total_qty += item.qty;
            total_amount += item.total_amount;

            // --- ЗМІНЕНО ТУТ ---
            // Використовуємо нове поле 'asset_type_name' для групування
            let type_name = item.asset_type_name || "Не вказано";

            if (!stats_by_type[type_name]) {
                stats_by_type[type_name] = { qty: 0, amount: 0 };
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

    // --- І ТУТ ---
    for (let type_name in stats_by_type) {
        html += `
                    <tr>
                        <td>${type_name}</td>
                        <td class="text-right">${format_number(stats_by_type[type_name].qty)}</td>
                        <td class="text-right">${format_currency(stats_by_type[type_name].amount)}</td>
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
