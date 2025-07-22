// Copyright (c) 2024, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on('oiHardware', {
    /**
     * Головна функція, що спрацьовує при оновленні форми.
     */
    refresh: function (frm) {
        // Запускаємо налаштування кнопок та перерахунок підсумків
        frm.trigger('setup_buttons');
        frm.trigger('recalculate_totals');
    },

    /**
     * Налаштовує видимість кастомних кнопок.
     */
    setup_buttons: function (frm) {
        frm.remove_custom_button(__('Додати партію'));
        frm.remove_custom_button(__('Історія переміщень'));


        frm.add_custom_button(__('Додати партію'), () => {
            // Викликаємо кастомну подію "add_batch_items"
            frm.trigger('add_batch_items');
        });


        if (!frm.is_new()) {
            frm.add_custom_button(__('Історія переміщень'), () => {
                // Викликаємо кастомну подію "show_movement_history"
                frm.trigger('show_movement_history');
            });
        }
    },

    /**
     * Показує історію переміщень.
     */
    show_movement_history: function (frm) {
        frappe.route_options = {
            "hardware_list.hardware_type": frm.doc.name
        };
        frappe.set_route("List", "oiHardware Transfer");
    },

    /**
     * Відкриває діалог для масового створення елементів.
     */
    add_batch_items: function (frm) {
        if (!frm.doc.title) {
            frappe.msgprint(__('Будь ласка, спочатку введіть "Назву активу".'));
            return;
        }

        let d = new frappe.ui.Dialog({
            title: __('Введіть кількість для створення'),
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
                frm.trigger('recalculate_totals'); // Використовуємо trigger
                d.hide();
            }
        });
        d.show();
    },

    /**
     * Перераховує підсумкові значення.
     */
    recalculate_totals: function (frm) {
        let total_qty = (frm.doc.asset_items || []).length;
        let total_cost = (frm.doc.unit_cost || 0) * total_qty;
        frm.set_value('quantity', total_qty);
        frm.set_value('purchase_cost', total_cost);
    },

    unit_cost: function (frm) { frm.trigger('recalculate_totals'); },

    asset_items_on_form_rendered: function (frm) {
        frm.trigger('recalculate_totals');
    }
});