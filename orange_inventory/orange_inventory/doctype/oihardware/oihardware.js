frappe.ui.form.on('oiHardware', {
    refresh: function (frm) {
        frm.trigger('toggle_fields');
        frm.trigger('calculate_total_cost');
        frm.remove_custom_button(__('Історія переміщень'));
        if (!frm.is_new()) {
            frm.add_custom_button(__('Історія переміщень'), () => {
                frm.trigger('show_transfer_history');
            });
        }
    },
    show_transfer_history: function (frm) {
        frappe.call({
            method: "orange_inventory.orange_inventory.doctype.oiasset_transfer.oiasset_transfer.get_history_for_asset",
            args: { asset_name: frm.doc.name },
            callback: function (r) {
                // ... (код для створення діалогового вікна з таблицею, як у попередній відповіді) ...
            }
        });
    },
    is_batched: function (frm) {
        frm.trigger('toggle_fields');
        frm.trigger('calculate_total_cost');
    },

    toggle_fields: function (frm) {
        // Показуємо або ховаємо поля в залежності від прапорця
        frm.toggle_display('serial_no', !frm.doc.is_batched);
        frm.toggle_display('quantity', frm.doc.is_batched);

        // Встановлюємо значення за замовчуванням при перемиканні
        if (frm.doc.is_batched) {
            frm.set_df_property('serial_number', 'reqd', 0);
            frm.set_df_property('quantity', 'reqd', 1);
        } else {
            frm.set_value('quantity', 1);
            frm.set_df_property('quantity', 'reqd', 0);
            frm.set_df_property('serial_number', 'reqd', 1);
        }
    },

    calculate_total_cost: function (frm) {
        let qty = frm.doc.is_batched ? (frm.doc.quantity || 0) : 1;
        let total = (frm.doc.unit_cost || 0) * qty;
        frm.set_value('total_cost', total);
    },

    unit_cost: function (frm) { frm.trigger('calculate_total_cost'); },
    quantity: function (frm) { frm.trigger('calculate_total_cost'); }
});