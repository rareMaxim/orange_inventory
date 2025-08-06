// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

/**
 * Функція для розрахунку загальної суми активу.
 */
let calculate_total_amount = function (frm) {
    let cost = flt(frm.doc.cost);
    let qty = flt(frm.doc.quantity);
    let total_amount = cost * qty;
    frm.doc.total = total_amount;
    frm.refresh_field('total');
};

frappe.ui.form.on("oiAsset", {
    refresh(frm) {
        calculate_total_amount(frm);
    },
    cost(frm) {
        calculate_total_amount(frm);
    },
    qty(frm) {
        calculate_total_amount(frm);
    }
});
