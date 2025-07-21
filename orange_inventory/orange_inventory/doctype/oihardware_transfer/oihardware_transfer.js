frappe.ui.form.on('oiHardware Transfer', {
    /**
     * Функція для перерахунку загальної вартості всього документа.
     * @param {object} frm - Об'єкт форми.
     */
    calculate_total_amount: function (frm) {
        let total = 0;
        if (frm.doc.hardware_list) {
            frm.doc.hardware_list.forEach(item => {
                total += item.amount || 0; // Додаємо суму рядка до загальної суми
            });
        }
        frm.set_value('total_amount', total);
        frm.refresh_field('total_amount');
    },

    /**
     * Спрацьовує при завантаженні або оновленні форми.
     * @param {object} frm - Об'єкт форми.
     */
    refresh: function (frm) {
        frm.events.calculate_total_amount(frm);
    }
});

frappe.ui.form.on('oiHardware Transfer Item', {
    /**
     * Спрацьовує, коли користувач обирає обладнання в рядку.
     * @param {object} frm - Об'єкт головної форми.
     * @param {string} cdt - Тип дочірнього документа ('oiHardware Transfer Item').
     * @param {string} cdn - Ім'я дочірнього документа (унікальний хеш рядка).
     */
    hardware: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        if (!item.hardware) {
            frappe.model.set_value(cdt, cdn, 'quantity', 0);
            frappe.model.set_value(cdt, cdn, 'cost', 0);
            frappe.model.set_value(cdt, cdn, 'amount', 0);
            frm.events.calculate_total_amount(frm);
            return;
        }

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "oiHardware",
                filters: { name: item.hardware },
                fieldname: ["unit_cost"]
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'cost', r.message.unit_cost || 0);
                    frappe.model.set_value(cdt, cdn, 'quantity', 1);
                    let amount = (r.message.unit_cost || 0) * 1;
                    frappe.model.set_value(cdt, cdn, 'amount', amount);
                    frm.events.calculate_total_amount(frm);
                }
            }
        });
    },

    /**
     * Спрацьовує, коли змінюється кількість в рядку.
     * @param {object} frm - Об'єкт головної форми.
     * @param {string} cdt - Тип дочірнього документа.
     * @param {string} cdn - Ім'я дочірнього документа.
     */
    quantity: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        let amount = (item.cost || 0) * (item.quantity || 0);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
        frm.events.calculate_total_amount(frm);
    },

    /**
     * Спрацьовує, коли рядок видаляється з таблиці.
     * @param {object} frm - Об'єкт головної форми.
     */
    hardware_list_remove: function (frm) {
        frm.events.calculate_total_amount(frm);
    }
});