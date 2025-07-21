// Copyright (c) 2024, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiHardware", {
    /**
     * Ця функція перераховує загальну вартість.
     */
    calculate_total_cost: function (frm) {
        let total = frm.doc.unit_cost * frm.doc.quantity;
        frm.set_value('purchase_cost', total);
    },

    refresh(frm) {
        frm.toggle_display('quantity', frm.doc.is_batched_asset);
        updateModelFilters(frm);
    },
    /**
     * Спрацьовує при зміні прапорця "Партіонний актив".
     */
    is_batched_asset: function (frm) {
        if (!frm.doc.is_batched_asset) {
            // Якщо актив не партійний, кількість завжди 1.
            frm.set_value('quantity', 1);
        }
        frm.toggle_display('quantity', frm.doc.is_batched_asset);
        frm.events.calculate_total_cost(frm);
    },

    /**
     * Спрацьовує при зміні вартості за одиницю.
     */
    unit_cost: function (frm) {
        frm.events.calculate_total_cost(frm);
    },

    /**
     * Спрацьовує при зміні кількості.
     */
    quantity: function (frm) {
        frm.events.calculate_total_cost(frm);
    },
    type(frm) {
        updateModelFilters(frm);
    }
});
function updateModelFilters(frm) {
    frm.set_query("model", function () {
        return {
            "filters": getModelFilters(frm)
        };
    });
};

function getModelFilters(frm) {
    var filters = {};
    if (frm.doc.type) {
        filters["type"] = frm.doc.type
    };
    if (frm.doc.manufacturer) {
        filters["manufacturer"] = frm.doc.manufacturer
    }
    return filters;
};

