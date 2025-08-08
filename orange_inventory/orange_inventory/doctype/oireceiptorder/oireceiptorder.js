frappe.ui.form.on('oiReceiptOrder', {
    refresh(frm) {
        // При оновленні форми, запускаємо валідацію для всіх існуючих рядків
        frm.doc.items.forEach(item => {
            validate_serials_for_row(frm, item.doctype, item.name);
        });
        update_dashboard(frm);
    },
    items_remove(frm) {
        update_dashboard(frm);
    },
    validate(frm) {
        // Додаткова перевірка перед збереженням
        let is_valid = true;
        frm.doc.items.forEach(item => {
            const { count, expected } = parse_serials(item.serial_numbers, item.qty);
            if (count !== expected) {
                is_valid = false;
                frappe.msgprint({
                    title: __('Помилка валідації'),
                    indicator: 'red',
                    message: __("Для активу '{0}' кількість серійних номерів ({1}) не співпадає з заявленою кількістю ({2}).", [item.asset_name, count, expected])
                });
            }
        });
        if (!is_valid) {
            frappe.validated = false;
        }
    }
});

frappe.ui.form.on('oiReceiptOrderItem', {
    qty(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn); // Використовуємо глобальну функцію
        validate_serials_for_row(frm, cdt, cdn);
        update_dashboard(frm);
    },
    rate(frm, cdt, cdn) {
        calculate_row_total(frm, cdt, cdn); // Використовуємо глобальну функцію
        update_dashboard(frm);
    },
    asset_type(frm) {
        // Затримка потрібна, щоб Frappe встиг виконати "fetch" для нового поля
        setTimeout(() => update_dashboard(frm), 200);
    },
    items_add(frm, cdt, cdn) {
        let items = frm.doc.items;
        if (items.length > 1) {
            let previous_asset_type = items[items.length - 2].asset_type;
            let new_row = items[items.length - 1];
            new_row.asset_type = previous_asset_type;
            frm.refresh_field('items');
        }
    },
    asset_name(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.asset_name) {
            let sanitized_name = row.asset_name.replace(/\s+/g, ' ').trim();
            frappe.model.set_value(cdt, cdn, 'asset_name', sanitized_name, true);
        }
    },
    serial_numbers(frm, cdt, cdn) {
        validate_serials_for_row(frm, cdt, cdn);
    },
});

let calculate_total_amount = function (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let total = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'total_amount', total);
    frm.refresh_field('items');
};

// -- ЛОГІКА ВАЛІДАЦІЇ СЕРІЙНИХ НОМЕРІВ --

/**
 * Розбирає рядок з серійними номерами, рахує їх та перевіряє на дублікати.
 * @param {string} serials_string - Рядок для аналізу.
 * @param {number} expected_qty - Очікувана кількість.
 * @returns {object} - Об'єкт з результатами аналізу.
 */
function parse_serials(serials_string, expected_qty) {
    if (!serials_string) {
        return { count: 0, expected: expected_qty, has_duplicates: false };
    }
    const serials_list = serials_string.replace(/\\n/g, ',').split(',').map(s => s.trim()).filter(s => s);
    const unique_serials = new Set(serials_list);
    return {
        count: serials_list.length,
        expected: expected_qty,
        has_duplicates: serials_list.length !== unique_serials.size
    };
}

/**
 * Оновлює HTML-підказку для конкретного рядка.
 * @param {object} frm - Об'єкт форми.
 * @param {string} cdt - doctype рядка.
 * @param {string} cdn - name рядка.
 */
function validate_serials_for_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const grid_row = frm.fields_dict.items.grid.get_row(cdn);
    const { count, expected, has_duplicates } = parse_serials(row.serial_numbers, row.qty);

    let message = '';
    let color = 'gray';

    if (row.qty > 1) { // Показуємо підказку тільки для групових активів
        if (count !== expected) {
            color = 'red';
            message = `Введено: ${count} / ${expected}`;
        } else {
            color = 'green';
            message = `Введено: ${count} / ${expected}`;
        }

        if (has_duplicates) {
            color = 'red';
            message += ' <br><b>Увага: є дублікати!</b>';
        }
    }

    const feedback_html = `<div style="color: ${color}; font-size: 12px; margin-top: 5px;">${message}</div>`;

    // Оновлюємо HTML поле та оновлюємо відображення
    frappe.model.set_value(cdt, cdn, 'serials_feedback', feedback_html);
    grid_row.refresh_field('serials_feedback');
}

let update_dashboard = function (frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frm.fields_dict.dashboard.html('');
        return;
    }

    let total_qty = 0;
    let total_amount = 0;
    let stats_by_type = {};

    frm.doc.items.forEach(item => {
        if (item.asset_name) {
            total_qty += item.qty;
            total_amount += item.total_amount;

            // --- ЗМІНЕНО ТУТ ---
            // Використовуємо нове поле 'asset_type_name' для групування
            let type_name = item.asset_type_name || "Не вказано";

            if (!stats_by_type[type_name]) {
                stats_by_type[type_name] = { qty: 0, amount: 0 };
            }
            stats_by_type[type_name].qty += item.qty;
            stats_by_type[type_name].amount += item.total_amount;
        }
    });

    let html = `
        <div style="padding: 10px;">
            <h4>Загальні показники</h4>
            <div class="row">
                <div class="col-md-6">
                    <div class="card" style="margin-bottom: 10px;">
                        <div class="card-body">
                            <h5 class="card-title">${format_number(total_qty)} од.</h5>
                            <p class="card-text text-muted">Всього одиниць</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card" style="margin-bottom: 10px;">
                        <div class="card-body">
                            <h5 class="card-title">${format_currency(total_amount)}</h5>
                            <p class="card-text text-muted">Загальна вартість</p>
                        </div>
                    </div>
                </div>
            </div>
            <hr>
            <h4>В розрізі типів</h4>
            <table class="table table-bordered table-sm">
                <thead>
                    <tr>
                        <th>Тип активу</th>
                        <th class="text-right">Кількість</th>
                        <th class="text-right">Сума</th>
                    </tr>
                </thead>
                <tbody>
    `;

    // --- І ТУТ ---
    for (let type_name in stats_by_type) {
        html += `
                    <tr>
                        <td>${type_name}</td>
                        <td class="text-right">${format_number(stats_by_type[type_name].qty)}</td>
                        <td class="text-right">${format_currency(stats_by_type[type_name].amount)}</td>
                    </tr>
        `;
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    frm.fields_dict.dashboard.html(html);
};
