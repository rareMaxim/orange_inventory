/**
 * Універсальні утиліти для Orange Inventory
 */

/**
 * Форматує число з двома знаками після коми.
 * @param {number} num - Число для форматування.
 * @returns {string} - Відформатоване число як рядок.
 */
function format_number(num) {
    if (num === undefined || num === null) return '';
    return new Intl.NumberFormat('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
};

/**
 * Форматує число як валюту у гривні.
 * @param {number} num - Число для форматування.
 * @returns {string} - Відформатована сума як рядок (напр., "1 234,56 ₴").
 */
function format_currency(num) {
    if (num === undefined || num === null) return '';
    return new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(num);
};

/**
 * Розраховує загальну суму для рядка дочірньої таблиці (кількість * ціна).
 * @param {object} frm - Об'єкт головної форми.
 * @param {string} cdt - Назва дочірнього доктайпа.
 * @param {string} cdn - Ідентифікатор рядка.
 * @param {string} table_field - Назва поля таблиці (за замовчуванням 'items').
 * @param {string} qty_field - Назва поля кількості (за замовчуванням 'qty').
 * @param {string} rate_field - Назва поля ціни (за замовчуванням 'rate').
 * @param {string} total_field - Назва поля загальної суми (за замовчуванням 'total_amount').
 */
function calculate_row_total(frm, cdt, cdn, { table_field = 'items', qty_field = 'qty', rate_field = 'rate', total_field = 'total_amount' } = {}) {
    let row = locals[cdt][cdn];
    let total = flt(row[qty_field]) * flt(row[rate_field]);
    frappe.model.set_value(cdt, cdn, total_field, total);
    frm.refresh_field(table_field);
};