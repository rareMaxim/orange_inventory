# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class oiCorrespondence(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        addressee: DF.Link | None
        case_number: DF.Data | None
        classification_code: DF.Data | None
        correspondence_type: DF.Literal["\u0412\u0445\u0456\u0434\u043d\u0438\u0439", "\u0412\u0438\u0445\u0456\u0434\u043d\u0438\u0439"]
        correspondent: DF.Link | None
        deadline_date: DF.Date | None
        execution_notes: DF.TextEditor | None
        executor: DF.Link | None
        external_date: DF.Date | None
        external_number: DF.Data | None
        registration_date: DF.Date | None
        registration_index: DF.Data | None
        resolution: DF.TextEditor | None
        scan: DF.Attach | None
        sequential_number: DF.Int
        summary: DF.TextEditor
        title: DF.Data | None
    # end: auto-generated types

    def before_save(self):
        # Встановлюємо заголовок документу для зручності
        self.title = f"{self.correspondence_type} № {self.registration_index} від {self.registration_date}"

    def before_insert(self):
        """Виконується перед першим збереженням документа для генерації номера."""
        self.generate_registration_index()

    def generate_registration_index(self):
        """Генерує унікальний реєстраційний індекс."""
        if not self.classification_code:
            frappe.throw(
                "Будь ласка, заповніть поле 'Код класифікації' перед збереженням.")

        current_year = getdate(self.registration_date).year

        # Знаходимо останній порядковий номер для цього типу та року
        last_sequential_number = frappe.db.get_value(
            "oiCorrespondence",
            {
                "correspondence_type": self.correspondence_type,
                # Фільтруємо по року з дати реєстрації
                "registration_date": ("between", [f"{current_year}-01-01", f"{current_year}-12-31"]),
            },
            "sequential_number",
            order_by="sequential_number DESC",
        )

        # Якщо номерів цього року ще не було, починаємо з 1
        new_sequential_number = (last_sequential_number or 0) + 1

        self.sequential_number = new_sequential_number
        self.registration_index = f"{self.sequential_number}/{self.classification_code}"
