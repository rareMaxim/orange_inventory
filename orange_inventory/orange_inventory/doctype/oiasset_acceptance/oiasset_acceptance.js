// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on('oiAsset Acceptance', {
    /**
     * Спрацьовує при завантаженні або оновленні основної форми.
     */
    refresh: function (frm) {
        // Запускаємо перерахунок тільки один раз при завантаженні
        frm.trigger('calculate_aggregate_totals');
    },

    /**
     * Ця функція тепер відповідає ТІЛЬКИ за підрахунок загальних сум,
     * читаючи вже готові дані з таблиці.
     */
    calculate_aggregate_totals: function (frm) {
        let total_amount = 0;
        let category_totals = {};

        (frm.doc.items || []).forEach(item => {
            // Просто читаємо суму з рядка
            let amount = item.amount || 0;
            total_amount += amount;

            if (item.asset_category) {
                category_totals[item.asset_category] = (category_totals[item.asset_category] || 0) + amount;
            }
        });

        // Форматуємо та встановлюємо суми
        let category_summary = [];
        for (const [category, sum] of Object.entries(category_totals)) {
            category_summary.push(`${category}: ${frappe.format(sum, { fieldtype: 'Currency' })}`);
        }

        // Використовуємо frm.set_value, але оскільки це відбувається в кінці ланцюжка,
        // це не буде викликати зайвих оновлень.
        frm.set_value('total_amount', total_amount);
        frm.set_value('category_totals', category_summary.join('\n'));
    }
});


frappe.ui.form.on('oiAsset Acceptance Item', {
    /**
     * Ця функція тепер відповідає ТІЛЬКИ за розрахунок суми
     * всередині свого власного рядка.
     */
    calculate_row_amount: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let amount = (row.unit_cost || 0) * (row.quantity || 0);
        // Встановлюємо значення тільки для цього рядка.
        // Це робить форму "брудною", що правильно, бо дані змінилися.
        frappe.model.set_value(cdt, cdn, 'amount', amount);
    },

    // Обробники подій для полів у рядку
    unit_cost: function (frm, cdt, cdn) {
        frm.get_field('items').grid.get_row(cdn).trigger('calculate_row_amount');
    },
    quantity: function (frm, cdt, cdn) {
        frm.get_field('items').grid.get_row(cdn).trigger('calculate_row_amount');
    },

    /**
     * Коли сума в рядку змінилася, ми викликаємо перерахунок
     * загальних сум у "шапці".
     */
    amount: function (frm, cdt, cdn) {
        frm.trigger('calculate_aggregate_totals');
    },

    // Перераховуємо загальну суму, якщо рядок видалено
    items_remove: function (frm) {
        frm.trigger('calculate_aggregate_totals');
    }
});