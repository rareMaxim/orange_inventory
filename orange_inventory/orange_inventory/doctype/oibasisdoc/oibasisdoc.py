# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import format_date


class oiBasisDoc(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        basis_doc_type: DF.Literal["\u0420\u0456\u0448\u0435\u043d\u043d\u044f"]
        decision_date: DF.Date
        decision_number: DF.Data
        full_title: DF.Data | None
        scan: DF.Attach | None
        title: DF.SmallText
    # end: auto-generated types

    def generate_full_title(self):
        """
        Формує повний заголовок на основі типу, номера та дати документа.
        """
        if self.decision_number and self.decision_date:
            # Форматуємо дату у звичний для України формат ДД.ММ.РРРР
            formatted_date = format_date(self.decision_date, "dd.MM.yyyy")

            # Створюємо рядок
            self.full_title = f"{self.basis_doc_type} №{self.decision_number} від {formatted_date}"
        else:
            # Якщо якісь дані відсутні, використовуємо стандартний заголовок
            self.full_title = self.title

    def before_save(self):
        self.generate_full_title()
