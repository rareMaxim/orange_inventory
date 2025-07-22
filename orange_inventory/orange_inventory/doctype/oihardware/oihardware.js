frappe.ui.form.on('oiHardware', {
    refresh: function (frm) {
        frm.trigger('setup_buttons');
        frm.trigger('recalculate_totals');
    },

    setup_buttons: function (frm) {
        frm.remove_custom_button(__('Створити активи'));

        if (!frm.is_new()) {
            frm.add_custom_button(__('Створити активи'), () => {
                frm.trigger('create_asset_items_dialog');
            });
        }
    },

    create_asset_items_dialog: function (frm) {
        if (!frm.doc.item_name) {
            frappe.msgprint(__('Будь ласка, введіть та збережіть "Назву активу".'));
            return;
        }

        let d = new frappe.ui.Dialog({
            title: __('Створення партії активів'),
            fields: [
                { label: 'Кількість', fieldname: 'qty', fieldtype: 'Int', reqd: 1 },
                { label: 'Початковий номер', fieldname: 'start_no', fieldtype: 'Int', default: 1 }
            ],
            primary_action_label: __('Створити'),
            primary_action(values) {
                // Викликаємо нашу нову, правильну серверу функцію
                frappe.call({
                    method: 'orange_inventory.orange_inventory.doctype.oihardware.oihardware.create_batch_assets',
                    args: {
                        hardware_doc_name: frm.doc.name,
                        qty: values.qty,
                        start_no: values.start_no
                    },
                    callback: function () {
                        // Просто оновлюємо форму, щоб побачити зміни
                        frm.reload_doc();
                        frappe.msgprint(__('Активи успішно створено'));
                    }
                });
                d.hide();
            }
        });
        d.show();
    },

    recalculate_totals: function (frm) {
        let total_qty = (frm.doc.assets || []).length;
        let total_cost = (frm.doc.unit_cost || 0) * total_qty;
        frm.set_value('total_quantity', total_qty);
        frm.set_value('total_cost', total_cost);
    },

    unit_cost: function (frm) {
        frm.trigger('recalculate_totals');
    }
});