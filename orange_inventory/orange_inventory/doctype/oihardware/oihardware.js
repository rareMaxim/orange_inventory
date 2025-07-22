// Copyright (c) 2024, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on('oiHardware', {
    /**
     * Ця функція спрацьовує щоразу при відкритті або оновленні форми.
     * Це ідеальне місце для керування кнопками.
     */
    refresh: function (frm) {
        // Спочатку очищаємо старі кнопки, щоб уникнути дублювання
        frm.remove_custom_button('Додати партію');
        frm.remove_custom_button('Історія переміщень');

        // Додаємо кнопку "Додати партію" ТІЛЬКИ якщо це новий документ
        if (frm.is_new()) {
            frm.add_custom_button(__('Додати партію'), function () {
                frm.cscript.add_batch_items(frm);
            }, __('Дії'));
        }

        // Додаємо кнопку "Історія переміщень" ТІЛЬКИ якщо документ вже збережено
        if (!frm.is_new()) {
            frm.add_custom_button(__('Історія переміщень'), function () {
                frm.cscript.show_movement_history(frm);
            }, __('Дії'));
        }

        // Перераховуємо підсумки при кожному оновленні
        frm.trigger('recalculate_totals');
    },

    /**
     * Показує відфільтрований список документів переміщення.
     */
    show_movement_history: function (frm) {
        frappe.route_options = {
            "hardware_list.hardware_type": frm.doc.name
        };
        frappe.set_route("List", "oiHardware Transfer");
    },

    /**
     * Викликає діалогове вікно для додавання партії елементів.
     */
    add_batch_items: function (frm) {
        let d = new frappe.ui.Dialog({
            title: __('Введіть кількість'),
            fields: [{ label: __('Кількість'), fieldname: 'qty', fieldtype: 'Int', reqd: 1 }],
            primary_action_label: __('Створити'),
            primary_action(values) {
                if (values.qty <= 0) return;
                frm.clear_table('asset_items');
                for (let i = 0; i < values.qty; i++) {
                    let item = frm.add_child('asset_items', {
                        hardware_type: frm.doc.name,
                        status: 'На складі'
                    });
                    let padded_index = String(i + 1).padStart(5, '0');
                    item.serial_no = `${frm.doc.item_name}-${padded_index}`;
                }
                frm.refresh_field('asset_items');
                frm.trigger('recalculate_totals');
                d.hide();
            }
        });
        d.show();
    },

    /**
     * Перераховує загальну кількість та вартість.
     */
    recalculate_totals: function (frm) {
        let total_qty = (frm.doc.asset_items || []).length;
        let total_cost = (frm.doc.unit_cost || 0) * total_qty;
        frm.set_value('quantity', total_qty);
        frm.set_value('purchase_cost', total_cost);
    },

    // Обробники для перерахунку при зміні даних
    unit_cost: function (frm) { frm.trigger('recalculate_totals'); },
    asset_items_on_form_rendered: function (frm) { frm.trigger('recalculate_totals'); }
});
