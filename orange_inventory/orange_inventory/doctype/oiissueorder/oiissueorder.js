// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt


frappe.ui.form.on("oiIssueOrder", "refresh", function (frm) {
    frm.fields_dict['items'].grid.get_field('asset').get_query = function (doc, cdt, cdn) {
        var child = locals[cdt][cdn];
        //console.log(child);
        return {
            filters: [
                ['current_owner', '=', frm.doc.from_organization],
            ]
        }
    }
});

frappe.ui.form.on('oiIssueOrder', {
    /**
     * Спрацьовує при зміні організації-відправника.
     * Якщо таблиця активів не порожня, запитує підтвердження у користувача.
     */
    from_organization: function (frm) {
        if (frm.doc.items && frm.doc.items.length > 0) {
            // Запитуємо підтвердження у користувача
            frappe.confirm(
                'Зміна організації-відправника очистить таблицю активів. Продовжити?',
                () => {
                    // Якщо користувач погодився, очищаємо таблицю
                    frm.set_value('items', []);
                    frm.refresh_field('items');
                },
                () => {
                    // Якщо відмовився, повертаємо попереднє значення
                    frm.set_value('from_organization', frm.doc.from_organization);
                }
            );
        }
    },
    /**
     * Головна подія, що спрацьовує при завантаженні та оновленні форми.
     */
    refresh: function (frm) {

    },
    items_remove(frm) {
        update_dashboard(frm);
    }
});

frappe.ui.form.on('oiIssueOrderItem', {

    /**
     * Спрацьовує, коли користувач обирає актив в ОДНОМУ рядку.
     * Оновлює залишок та інфографіку для миттєвого фідбеку.
     */
    asset: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.asset) {
            frappe.db.get_value('oiAsset', row.asset, ['quantity', 'cost'])
                .then(r => {
                    if (r) {
                        frappe.model.set_value(cdt, cdn, 'available_qty', r.quantity);
                    }
                });
        } else {
            frappe.model.set_value(cdt, cdn, 'available_qty', 0);
        }
    },
    /**
     * Спрацьовує при зміні кількості в рядку для оновлення дашборду.
     */
    qty(frm) {

    }
});

/**
 * НОВА ФУНКЦІЯ:
 * Проходить по ВСІХ рядках таблиці та оновлює для кожного з них
 * актуальний залишок на складі. Після цього оновлює дашборд.
 */
function update_all_rows(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        return;
    }

    const promises = frm.doc.items.map(item => {
        if (item.asset) {
            return frappe.db.get_value('oiAsset', item.asset, 'quantity')
                .then(r => {
                    if (r?.message?.quantity) {
                        // Встановлюємо значення безпосередньо, без виклику refresh_field
                        item.available_qty = r.message.quantity;
                    }
                });
        }
        // Повертаємо пустий проміс для рядків без активу
        return Promise.resolve();
    });

    // Promise.all чекає, доки всі запити до бази даних завершаться
    Promise.all(promises).then(() => {
        // Тільки після того, як всі дані оновлені, один раз оновлюємо таблицю
        frm.refresh_field('items');
    });
}
