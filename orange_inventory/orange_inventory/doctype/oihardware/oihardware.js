// Copyright (c) 2024, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiHardware", {
    refresh(frm) {
        updateModelFilters(frm);
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

