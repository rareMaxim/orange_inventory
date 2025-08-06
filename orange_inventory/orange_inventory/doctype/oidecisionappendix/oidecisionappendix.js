// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt
/**
 * Функція, що керує видимістю колонки "Причина повернення".
 * @param {object} frm - Об'єкт форми 'Order'.
 */
function toggle_return_column(frm) {
    // 1. Отримуємо поточний статус замовлення
    const is_new_assets = frm.doc.is_new_assets;

    // 2. Отримуємо об'єкт дочірньої таблиці (припустимо, її назва 'items')
    const grid = frm.get_field('items').grid;

    // 4. Застосовуємо умову до колонки 'return_reason'
    // grid.toggle_display('new_asset_name', should_show);
    // grid.toggle_enable("new_asset_name", false);
    // grid.set_column_disp('new_asset_name', should_show);
    grid.toggle_enable("new_asset_name", is_new_assets);
    grid.toggle_enable("existing_asset", !is_new_assets);

    // 5. Оновлюємо відображення таблиці
    grid.refresh();
}
frappe.ui.form.on("oiDecisionAppendix", {
    /**
     * Подія, що спрацьовує при завантаженні або оновленні форми.
     * Ідеальне місце для налаштування початкового стану видимості полів.
     */
    refresh(frm) {
        // set_grid_field_visibility(frm);
        toggle_return_column(frm);
    },
    is_new_assets(frm) {
        // Викликаємо функцію для зміни видимості колонки "Причина повернення"
        toggle_return_column(frm);
    }

});


// oidecisionappendix.js

frappe.ui.form.on('oiAssetTransferItem', {
    /**
     * Ця функція викликається, коли змінюється будь-яке з полів,
     * перерахованих нижче, у дочірній таблиці 'oiAssetTransferItem'.
     * @param {object} frm - Об'єкт головної форми (oiDecisionAppendix).
     * @param {string} cdt - Назва дочірнього доктайпа ('oiAssetTransferItem').
     * @param {string} cdn - Унікальний ідентифікатор рядка в таблиці.
     */
    qty: function (frm, cdt, cdn) {
        calculate_total_amount(frm, cdt, cdn);
    },
    rate: function (frm, cdt, cdn) {
        calculate_total_amount(frm, cdt, cdn);
    },
    items_add: function (frm, cdt, cdn) {

        // Після додавання нового рядка, встановлюємо значення по замовчуванню
        var child = locals[cdt][cdn]
        // frm.set_df_property('items', 'reqd', frm.doc.is_new_assets, frm.docname, 'existing_asset', child.name);
        // frm.set_df_property('items', 'reqd', !frm.doc.is_new_assets, frm.docname, 'new_asset_name', child.name)
    }
});

/**
 * Функція для розрахунку загальної суми для одного рядка.
 */
let calculate_total_amount = function (frm, cdt, cdn) {
    // Отримуємо доступ до даних конкретного рядка, в якому відбулися зміни.
    let row = locals[cdt][cdn];

    // Розраховуємо суму, переконуючись, що значення є числами.
    // Якщо одне з полів пусте, воно буде вважатися нулем.
    let total = flt(row.qty) * flt(row.rate);

    // Встановлюємо розраховане значення в поле 'Всього' ('total_amount')
    // Використовуємо frappe.model.set_value, оскільки це надійний спосіб,
    // який коректно оновлює дані та запускає пов'язані тригери.
    frappe.model.set_value(cdt, cdn, 'total_amount', total);

    // Оновлюємо відображення дочірньої таблиці на екрані,
    // щоб користувач одразу побачив зміни.
    frm.refresh_field('items');
};
