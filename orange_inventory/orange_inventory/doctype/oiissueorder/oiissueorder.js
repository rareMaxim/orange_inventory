// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on('oiIssueOrder', {
    refresh(frm) {
        update_dashboard(frm);
    },
    items_remove(frm) {
        update_dashboard(frm);
    }
});

frappe.ui.form.on('oiIssueOrderItem', {
    /**
     * Ця функція викликається, коли користувач обирає значення
     * в полі 'asset' (Актив) в дочірній таблиці.
     */
    asset: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Перевіряємо, чи є значення в полі "Актив"
        if (row.asset) {
            // Робимо запит до сервера, щоб отримати поле 'quantity'
            // з документа 'oiAsset', ID якого ми щойно обрали.
            frappe.db.get_value('oiAsset', row.asset, 'quantity')
                .then(r => {
                    // 'r' - це об'єкт з відповіддю від сервера
                    if (r && r.message.quantity !== undefined) {
                        // Встановлюємо отримане значення в наше поле "Доступно на складі"
                        frappe.model.set_value(cdt, cdn, 'available_qty', r.message.quantity);
                        frm.refresh_field('items');
                        update_dashboard(frm);
                    }
                });
        } else {
            // Якщо користувач очистив поле "Актив", ми також очищаємо залишок
            frappe.model.set_value(cdt, cdn, 'available_qty', 0);
            frm.refresh_field('items');
            update_dashboard(frm);
        }
    },
    qty(frm) {
        update_dashboard(frm);
    },
});

/**
 * Функція для збору даних та генерації HTML для дашборду.
 */
let update_dashboard = function (frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frm.fields_dict.dashboard.html('');
        return;
    }

    let total_qty = 0;
    let total_amount = 0;
    let stats_by_type = {};
    let asset_promises = [];

    frm.doc.items.forEach(item => {
        if (item.asset) {
            asset_promises.push(
                frappe.db.get_value('oiAsset', item.asset, ['asset_type', 'cost']).then(r => {
                    return { asset_data: r, item_data: item };
                })
            );
        }
    });

    Promise.all(asset_promises).then(results => {
        total_qty = 0; // Обнуляємо перед перерахунком
        total_amount = 0;
        stats_by_type = {};

        results.forEach(res => {
            let type_name = res.asset_data.asset_type || "Не вказано";
            let item_qty = res.item_data.qty;
            let item_cost = res.asset_data.cost || 0;
            let item_amount = item_qty * item_cost;

            total_qty += item_qty;
            total_amount += item_amount;

            if (!stats_by_type[type_name]) {
                stats_by_type[type_name] = { qty: 0, amount: 0 };
            }
            stats_by_type[type_name].qty += item_qty;
            stats_by_type[type_name].amount += item_amount;
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
                            <td>${type_name}</td>
                            <td class="text-right">${format_number(stats_by_type[type_name].qty, false)}</td>
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
    });
};

let format_number = (num, fractions = true) => {
    if (num === undefined || num === null) return '';
    const options = fractions ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : {};
    return new Intl.NumberFormat('uk-UA', options).format(num);
};

let format_currency = (num) => {
    if (num === undefined || num === null) return '';
    return new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(num);
};