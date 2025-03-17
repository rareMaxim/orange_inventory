// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt
async function set_labels_suggestions(frm) {
    frappe.db.get_list(frm.doc.doctype, {
        fields: ['task'],
    }).then((records) => {
        if (records.length > 0) {
            const options = records.map((item) => ({ value: item.task, label: item.task }));
            frm.fields_dict.task_copy.set_data(options)
        } else {
            frm.set_df_property("task", "options", []);
        }
    });
}

frappe.ui.form.on("oiWorkDaily", {
    refresh(frm) {
        // set_labels_suggestions(frm)
    },
    company(frm) {
        frm.set_query("employee", function () {
            return {
                "filters": {
                    "company": frm.doc.company,
                }
            };
        });
    }
});
