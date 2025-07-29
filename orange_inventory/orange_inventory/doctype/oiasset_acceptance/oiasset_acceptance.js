// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

// Функція для розрахунку суми в одному рядку
const calculate_row_total = (frm, cdt, cdn) => {
    const row = locals[cdt][cdn];
    // Розраховуємо суму, переконуючись, що значення не порожні
    const total = (row.quantity || 0) * (row.unit_cost || 0);
    // Встановлюємо значення в поле "Сума"
    frappe.model.set_value(cdt, cdn, "amount", total);
};
// Функція для розрахунку загальної кількості (клієнтська сторона)
function calculate_total_quantity(frm) {
    let total_qty = 0;
    if (frm.doc.items && frm.doc.items.length) {
        frm.doc.items.forEach(function (item) {
            total_qty += item.quantity || 0;
        });
    }
    // Встановлюємо значення без виклику 'dirty', оскільки це розрахункове поле
    frm.set_value('total_quantity', total_qty);
}

// Єдина функція для запуску всіх розрахунків
function run_all_calculations(frm) {
    // 1. Розрахунок загальної кількості (швидко, на клієнті)
    calculate_total_quantity(frm);

    // 2. Виклик серверного методу для розрахунку зведення по категоріях
    // Це оновить поле 'category_totals'
    frm.call('calculate_category_totals').then(r => {
        frm.refresh_field('category_totals');
    });
    calculate_category_totals(frm);
}

frappe.ui.form.on('oiAsset Acceptance', {

    // Викликаємо перерахунок при першому завантаженні форми
    refresh: function (frm) {
        // frm.trigger('recalculate_totals');
        run_all_calculations(frm);
    }
});


frappe.ui.form.on('oiAsset Acceptance Item', {
    /**
     * НОВА ФУНКЦІЯ: Спрацьовує при додаванні нового рядка в таблицю.
     */
    items_add: function (frm, cdt, cdn) {

        // // Отримуємо всі рядки
        const items = frm.doc.items;
        // Перевіряємо, чи це не перший рядок
        if (items.length > 1) {
            // Отримуємо дані з попереднього рядка
            const prev_row = items[items.length - 2];
            // Отримуємо поточний, щойно створений рядок
            let current_row = locals[cdt][cdn];
            // Встановлюємо категорію з попереднього рядка
            current_row.asset_category = prev_row.asset_category;
            // Оновлюємо відображення поля
            frm.refresh_field('items');
        }
        run_all_calculations(frm);
    },
    // При зміні будь-якого з цих полів, просто запускаємо
    // ОДНУ головну функцію перерахунку на батьківській формі.
    unit_cost: function (frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
        run_all_calculations(frm);
    },
    quantity: function (frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn);
        run_all_calculations(frm);
    },
    asset_category: function (frm, cdt, cdn) {
        run_all_calculations(frm);
    },
    items_remove: function (frm) {
        run_all_calculations(frm);
    }
});

// Основна функція для розрахунку та відображення даних
let calculate_category_totals = function(frm) {
    let items = frm.doc.items;
    let category_totals = {};
    let grand_total_qty = 0;
    let grand_total_amount = 0;

    // 1. Групування та підрахунок
    if (items && items.length) {
        items.forEach(item => {
            // Використовуємо 'Без категорії' якщо поле пусте
            let category = item.asset_category || 'Без категорії';
            if (!category_totals[category]) {
                category_totals[category] = { qty: 0, amount: 0 };
            }
            category_totals[category].qty += flt(item.quantity);
            category_totals[category].amount += flt(item.amount);
        });
    }

    // 2. Створення HTML-таблиці
    let html = `
        <div style="font-family: Arial, sans-serif; border: 1px solid #d1d8dd; border-radius: 4px; padding: 15px; margin-top: 10px;">
            <h5 style="margin-top: 0; margin-bottom: 15px; font-size: 16px; color: #333;">Зведена інформація за категоріями</h5>
            <table class="table table-bordered" style="width: 100%; border-collapse: collapse;">
                <thead style="background-color: #f7fafc;">
                    <tr>
                        <th style="padding: 8px; border: 1px solid #d1d8dd; text-align: center; width: 40px;">№</th>
                        <th style="padding: 8px; border: 1px solid #d1d8dd; text-align: left;">Категорія</th>
                        <th style="padding: 8px; border: 1px solid #d1d8dd; text-align: right;">Кількість</th>
                        <th style="padding: 8px; border: 1px solid #d1d8dd; text-align: right;">Сума</th>
                    </tr>
                </thead>
                <tbody>
    `;

    if (Object.keys(category_totals).length > 0) {
        let row_number = 1;
        // Сортуємо категорії за алфавітом для стабільного порядку
        Object.keys(category_totals).sort().forEach(category => {
            grand_total_qty += category_totals[category].qty;
            grand_total_amount += category_totals[category].amount;
            html += `
                <tr>
                    <td style="padding: 8px; border: 1px solid #d1d8dd; text-align: center;">${row_number}</td>
                    <td style="padding: 8px; border: 1px solid #d1d8dd;">${category}</td>
                    <td style="padding: 8px; border: 1px solid #d1d8dd; text-align: right;">${category_totals[category].qty}</td>
                    <td style="padding: 8px; border: 1px solid #d1d8dd; text-align: right;">${format_currency(category_totals[category].amount, frm.doc.currency)}</td>
                </tr>
            `;
            row_number++;
        });
    } else {
        html += `
            <tr>
                <td colspan="4" style="padding: 8px; text-align: center; color: #777;">Немає даних для відображення</td>
            </tr>
        `;
    }

    // 3. Додавання рядка "Всього"
    html += `
                </tbody>
                <tfoot style="font-weight: bold; background-color: #f7fafc;">
                    <tr>
                        <td colspan="2" style="padding: 8px; border: 1px solid #d1d8dd; text-align: left;">Всього</td>
                        <td style="padding: 8px; border: 1px solid #d1d8dd; text-align: right;">${grand_total_qty}</td>
                        <td style="padding: 8px; border: 1px solid #d1d8dd; text-align: right;">${format_currency(grand_total_amount, frm.doc.currency)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    `;

    // 4. Вставка HTML у поле та оновлення
    frm.set_df_property('category_totals', 'options', html);
    frm.refresh_field('category_totals');
};