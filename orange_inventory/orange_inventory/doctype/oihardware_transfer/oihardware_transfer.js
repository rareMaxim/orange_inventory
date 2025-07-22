frappe.ui.form.on('oiHardware Transfer', {
    calculate_total_amount: function (frm) {
        let total = 0;
        (frm.doc.hardware_list || []).forEach(item => { total += item.amount || 0; });
        frm.set_value('total_amount', total);
    },
    refresh: function (frm) {
        frm.events.calculate_total_amount(frm);
        // Встановлюємо фільтр, щоб показувати тільки активи на складі
        frm.set_query("asset_item", "hardware_list", function () {
            return {
                filters: {
                    status: "На складі"
                }
            };
        });
    }
});

frappe.ui.form.on('oiHardware Transfer Item', {
    asset_item: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        if (!item.asset_item) {
            frappe.model.set_value(cdt, cdn, 'amount', 0);
            frappe.model.set_value(cdt, cdn, 'hardware_type', '');
            frm.events.calculate_total_amount(frm);
            return;
        }

        // Робимо один запит, щоб отримати назву батьківського документа (тип)
        frappe.db.get_value('Asset Item', item.asset_item, 'parent')
            .then(r => {
                let parent_hardware_name = r.message.parent;
                // Записуємо назву типу в інформаційне поле
                frappe.model.set_value(cdt, cdn, 'hardware_type', parent_hardware_name);

                // Тепер робимо другий запит, щоб отримати вартість з цього типу
                frappe.db.get_value('oiHardware', parent_hardware_name, 'unit_cost')
                    .then(cost_r => {
                        let cost = cost_r.message.unit_cost || 0;
                        frappe.model.set_value(cdt, cdn, 'amount', cost);
                        frm.events.calculate_total_amount(frm);
                    });
            });
    },

    hardware_list_remove: function (frm) {
        frm.events.calculate_total_amount(frm);
    }
});