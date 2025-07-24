// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt


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
}

frappe.ui.form.on('oiAsset Acceptance', {
    /**
      * Головна функція для перерахунку всіх підсумків.
      * Вона тепер робить всю роботу сама, без зайвих викликів.
      */
    // recalculate_totals: function (frm) {
    //     let total_amount = 0;
    //     let category_totals = {};

    //     // Проходимо по кожному рядку в таблиці
    //     (frm.doc.items || []).forEach(item => {
    //         // Розраховуємо суму для рядка прямо тут
    //         let amount = (item.unit_cost || 0) * (item.quantity || 0);
    //         // Встановлюємо значення суми для рядка (тихо, без виклику подій)
    //         frappe.model.set_value(item.doctype, item.name, 'amount', amount);

    //         // Додаємо до загальної суми
    //         total_amount += amount;

    //         // Групуємо суми за категоріями
    //         if (item.asset_category) {
    //             category_totals[item.asset_category] = (category_totals[item.asset_category] || 0) + amount;
    //         }
    //     });

    //     // Форматуємо та встановлюємо суми за категоріями
    //     let category_summary = [];
    //     for (const [category, sum] of Object.entries(category_totals)) {
    //         category_summary.push(`${category}: ${frappe.format(sum, { fieldtype: 'Currency' })}`);
    //     }

    //     // Встановлюємо фінальні значення в "шапці" документа
    //     frm.set_value('total_amount', total_amount);
    //     frm.set_value('category_totals', category_summary.join('\n'));
    // },

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
        // const items = frm.doc.items;
        // // Перевіряємо, чи це не перший рядок
        // if (items.length > 1) {
        //     // Отримуємо дані з попереднього рядка
        //     const prev_row = items[items.length - 2];
        //     // Отримуємо поточний, щойно створений рядок
        //     let current_row = locals[cdt][cdn];
        //     // Встановлюємо категорію з попереднього рядка
        //     current_row.asset_category = prev_row.asset_category;
        //     // Оновлюємо відображення поля
        //     frm.refresh_field('items');
        // }
        run_all_calculations(frm);
    },
    // При зміні будь-якого з цих полів, просто запускаємо
    // ОДНУ головну функцію перерахунку на батьківській формі.
    unit_cost: function (frm, cdt, cdn) {
        run_all_calculations(frm);
    },
    quantity: function (frm, cdt, cdn) {
        run_all_calculations(frm);
    },
    asset_category: function (frm, cdt, cdn) {
        run_all_calculations(frm);
    },
    items_remove: function (frm) {
        run_all_calculations(frm);
    }
});