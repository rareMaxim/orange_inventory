frappe.ui.form.on('oiHardware Transfer', {
    /**
     * Функція для перерахунку загальної вартості всього документа.
     * @param {object} frm - Об'єкт форми.
     */
    calculate_total_amount: function (frm) {
        let total = 0;
        (frm.doc.hardware_list || []).forEach(item => { total += item.amount || 0; });
        frm.set_value('total_amount', total);
    },
    refresh: function (frm) {
        frm.events.calculate_total_amount(frm);
    }
});

frappe.ui.form.on('oiHardware Transfer Item', {
    hardware_type: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        // Скидаємо попередній вибір серійного номера, якщо він був
        frappe.model.set_value(cdt, cdn, 'asset_item', '');

        // Отримуємо доступ до поля 'asset_item' у поточному рядку таблиці
        let grid_row = frm.get_field('hardware_list').grid.get_row(cdn);

        // Встановлюємо динамічний фільтр для цього поля
        grid_row.get_field('asset_item').get_query = function () {
            return {
                filters: {
                    // Показувати тільки ті елементи, які належать до обраного типу
                    parent: item.hardware_type,
                    // І тільки ті, що є на складі
                    status: 'На складі'
                }
            };
        };
    },
    asset_item: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        if (!item.asset_item) {
            frappe.model.set_value(cdt, cdn, 'amount', 0);
            frm.events.calculate_total_amount(frm);
            return;
        }

        // Отримуємо вартість з головного документа 'oiHardware'
        frappe.db.get_value('oiHardware', item.hardware_type, 'unit_cost')
            .then(r => {
                let cost = r.message.unit_cost || 0;
                frappe.model.set_value(cdt, cdn, 'amount', cost);
                frm.events.calculate_total_amount(frm);
            });
    },
    /**
     * Спрацьовує, коли користувач змінює категорію в рядку.
     * Відправляє зміни на сервер для збереження в картці обладнання.
     */
    asset_category: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        // Перевіряємо, чи є що оновлювати
        if (item.hardware && item.asset_category) {
            frappe.call({
                // Вказуємо шлях до нашого нового серверного методу
                method: "orange_inventory.doctype.oihardware_transfer.oihardware_transfer.update_hardware_category",
                args: {
                    hardware_name: item.hardware,
                    new_category: item.asset_category
                },
                callback: function (r) {
                    if (!r.exc) {
                        // Якщо все пройшло успішно, показуємо повідомлення
                        frappe.show_alert({
                            message: __("Категорію для '{0}' оновлено", [item.hardware]),
                            indicator: 'green'
                        }, 5);
                    }
                    // Якщо є помилка, Frappe автоматично покаже її
                }
            });
        }
    },
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
                fieldname: ["unit_cost", "asset_category"]
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'asset_category', r.message.asset_category);
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