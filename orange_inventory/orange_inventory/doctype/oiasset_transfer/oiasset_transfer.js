// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiAsset Transfer", {
    refresh: function (frm) {
        // Оновлюємо статистику при завантаженні форми
        if (frm.doc.hardware_list && frm.doc.hardware_list.length > 0) {
            update_statistics(frm);
        } else {
            // Якщо таблиця порожня, очищуємо блок статистики
            $("#transfer-stats-wrapper").html("");
        }
    }
});

frappe.ui.form.on("oiAsset Transfer Item", {
    hardware_list_add: function (frm, cdt, cdn) {

        // // Отримуємо всі рядки
        const items = frm.doc.hardware_list;
        // Перевіряємо, чи це не перший рядок
        if (items.length > 1) {
            // Отримуємо дані з попереднього рядка
            const prev_row = items[items.length - 2];
            // Отримуємо поточний, щойно створений рядок
            let current_row = locals[cdt][cdn];
            // Встановлюємо категорію з попереднього рядка
            current_row.to_counterparty = prev_row.to_counterparty;
            // Оновлюємо відображення поля
            frm.refresh_field('hardware_list');
        }
        update_statistics(frm);
    },
    quantity: function (frm) { update_statistics(frm); },
    hardware: function (frm) { update_statistics(frm); },
    to_counterparty: function (frm) { update_statistics(frm); },
    hardware_list_remove: function (frm) {
        update_statistics(frm);
    }
});
// Головна функція для розрахунку та рендерингу статистики
function update_statistics(frm) {
    if (!frm.doc.hardware_list || frm.doc.hardware_list.length === 0) {
        $("#transfer-stats-wrapper").html("");
        return;
    }

    frm.call('get_hardware_details').then(r => {
        if (!r.message) return;

        const details_map = r.message.hardware_details || {};
        const counterparty_map = r.message.counterparty_names || {};

        let totals = { qty: 0, cost: 0 };
        // ОНОВЛЕНО: Створюємо вкладену структуру
        let by_counterparty_map = {};
        let counterparty_order = [];

        frm.doc.hardware_list.forEach(item => {
            const details = details_map[item.hardware];
            if (!details) return;

            const qty = item.is_batched ? (item.quantity || 0) : 1;
            const cost = (details.unit_cost || 0) * qty;
            const category = details.asset_category || "Без категорії";

            // 1. Рахуємо загальні суми
            totals.qty += qty;
            totals.cost += cost;

            // 2. Будуємо вкладену структуру по контрагентах та категоріях
            if (item.to_counterparty) {
                // Якщо контрагент зустрічається вперше, ініціалізуємо його
                if (!by_counterparty_map[item.to_counterparty]) {
                    counterparty_order.push(item.to_counterparty);
                    const name = counterparty_map[item.to_counterparty] || item.to_counterparty;
                    by_counterparty_map[item.to_counterparty] = {
                        name: name,
                        total_qty: 0,
                        total_cost: 0,
                        categories: {}
                    };
                }

                const cp_data = by_counterparty_map[item.to_counterparty];

                // Ініціалізуємо категорію всередині контрагента, якщо її немає
                if (!cp_data.categories[category]) {
                    cp_data.categories[category] = { qty: 0, cost: 0 };
                }

                // Агрегуємо дані
                cp_data.total_qty += qty;
                cp_data.total_cost += cost;
                cp_data.categories[category].qty += qty;
                cp_data.categories[category].cost += cost;
            }
        });

        const by_counterparty_data = { map: by_counterparty_map, order: counterparty_order };
        render_stats_html(frm, totals, by_counterparty_data);
    });
}

// Функція для генерації HTML
function render_stats_html(frm, totals, by_counterparty_data) {
    const currency = frm.doc.currency || "UAH";

    let html = `
        <div class="frappe-card">
            <div class="frappe-card-head">Загальна статистика</div>
            <div class="frappe-card-body">
                <div class="row">
                    <div class="col">
                        <div class="statistic-box">
                            <span class="statistic-value">${totals.qty}</span>
                            <span class="statistic-label">одиниць</span>
                        </div>
                    </div>
                    <div class="col">
                         <div class="statistic-box">
                            <span class="statistic-value">${format_currency(totals.cost, currency)}</span>
                            <span class="statistic-label">загальна вартість</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-4">
            ${generate_nested_breakdown_html(by_counterparty_data, currency)}
        </div>

        <style>
            .statistic-box { text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 6px; }
            .statistic-value { display: block; font-size: 2em; font-weight: 600; }
            .statistic-label { display: block; font-size: 0.9em; color: #6c757d; }
            .progress-bar-container { background-color: #e9ecef; border-radius: .25rem; }
            .progress-bar-fill { background-color: #0d6efd; height: 18px; border-radius: .25rem; text-align: right; color: white; padding-right: 5px; font-size: 12px; line-height: 18px; }
            .counterparty-header { font-weight: 500; font-size: 1.1em; }
        </style>
    `;

    $("#transfer-stats-wrapper").html(html);
}

// ОНОВЛЕНО: Ця функція тепер генерує вкладені картки
function generate_nested_breakdown_html(data, currency) {
    let final_html = '';
    const { map, order } = data;

    if (order.length === 0) {
        return '<p class="text-muted">Недостатньо даних для відображення.</p>';
    }

    order.forEach(counterparty_id => {
        const cp_data = map[counterparty_id];
        let category_rows = '';

        // Сортуємо категорії по назві для стабільного порядку
        const sorted_categories = Object.keys(cp_data.categories).sort();

        sorted_categories.forEach(category_name => {
            const cat_data = cp_data.categories[category_name];
            // Відсоток рахуємо відносно загальної суми для цього контрагента
            const percentage = cp_data.total_cost > 0 ? ((cat_data.cost / cp_data.total_cost) * 100).toFixed(1) : 0;

            category_rows += `
                <tr>
                    <td style="width: 35%; padding-left: 20px;">${category_name}</td>
                    <td style="width: 45%;">
                        <div class="progress-bar-container" title="${percentage}% від суми для отримувача">
                            <div class="progress-bar-fill" style="width: ${percentage}%;">${percentage}%</div>
                        </div>
                    </td>
                    <td style="width: 20%; text-align: right;"><strong>${format_currency(cat_data.cost, currency)}</strong> (${cat_data.qty} од.)</td>
                </tr>
            `;
        });

        final_html += `
            <div class="frappe-card mt-3">
                <div class="frappe-card-head counterparty-header d-flex justify-content-between">
                    <span>${cp_data.name}</span>
                    <span class="text-secondary">Всього: ${format_currency(cp_data.total_cost, currency)} (${cp_data.total_qty} од.)</span>
                </div>
                <div class="frappe-card-body">
                    <table class="table table-sm mb-0">${category_rows}</table>
                </div>
            </div>
        `;
    });

    return final_html;
}