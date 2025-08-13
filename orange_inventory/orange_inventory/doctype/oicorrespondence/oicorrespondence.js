// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiCorrespondence", {
    refresh(frm) {
        // Ця функція викликається при завантаженні та оновленні форми
        // Встановлюємо заголовок в залежності від стану документа
        if (frm.doc.title) {
            frm.set_intro(frm.doc.title);
        } else {
            frm.set_intro(__("Новий документ"));
        }
    },

    correspondence_type(frm) {
        // Очищуємо поля при зміні типу, щоб уникнути збереження некоректних даних
        if (frm.doc.correspondence_type === "Вхідний") {
            frm.set_value("addressee", null);
        } else if (frm.doc.correspondence_type === "Вихідний") {
            frm.set_value("correspondent", null);
            frm.set_value("external_number", null);
            frm.set_value("external_date", null);
            frm.set_value("resolution", null);
            frm.set_value("deadline_date", null);
            frm.set_value("execution_notes", null);
        }
    }
});