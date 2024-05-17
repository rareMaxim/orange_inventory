// Copyright (c) 2024, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiBarcodeScanner", {
    refresh(frm) {

    },
    scan_it(frm) {
        new frappe.qr.ScannerTools({
            dialog: true, // open camera scanner in a dialog
            multiple: true, // stop after scanning one value
            on_scan(data) {
                frappe.set_route("Form", "oiHardware", data.decodedText);
            }
        });
        // new frappe.ui.ScannerTools({
        //     dialog: true,
        //     on_devices(data) {
        //         console.log(data);
        //         frappe.show_alert({
        //             message: (JSON.stringify(data)),
        //             indicator: 'green'
        //         }, 5);
        //     }
        // });
    },
});
