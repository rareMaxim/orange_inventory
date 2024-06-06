// Copyright (c) 2024, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiHardwareTransfer", {
    onload(frm) {
        frappe.db.get_value('oiContract Type', frm.doc.name, 'from_balance', (r) => {
            console.log('Fetched value:', r.from_balance);
            //  if (r && r.from_balance) {

            // }
        });
    }
});
