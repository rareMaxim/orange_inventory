# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHardwareTransfer(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oihardware_transfer_item.oihardware_transfer_item import oiHardwareTransferItem

        amended_from: DF.Link | None
        basis_document: DF.Data | None
        from_counterparty: DF.Link
        hardware_list: DF.Table[oiHardwareTransferItem]
        status: DF.Data | None
        to_counterparty: DF.Link
        total_amount: DF.Currency
        transfer_date: DF.Date
    # end: auto-generated types

    def on_submit(self):
        """
        Спрацьовує при проведенні (Submit) документа.
        Обробляє кожну позицію в списку обладнання.
        """
        for item in self.hardware_list:
            # Завантажуємо документ обладнання, що передається
            hardware_doc = frappe.get_doc("oiHardware", item.hardware)

            # --- Логіка для обробки кількості ---
            if hardware_doc.is_batched_asset:
                # Це партійний актив. Перевіряємо залишок і зменшуємо його.
                if hardware_doc.quantity < item.quantity:
                    frappe.throw(f"Недостатньо залишків для '{hardware_doc.name}'. "
                                 f"На складі: {hardware_doc.quantity}, "
                                 f"Спроба передати: {item.quantity}")

                hardware_doc.quantity -= item.quantity

            # Додаємо запис в історію переміщень для всіх типів активів
            self._add_movement_log(hardware_doc, item.quantity)

            # Зберігаємо оновлений документ обладнання
            hardware_doc.save(ignore_permissions=True)

        # Оновлюємо статус самого документа StockTransfer
        self.db_set("status", "Завершено")

    def on_cancel(self):
        """
        Спрацьовує при скасуванні (Cancel) документа.
        Відкочує всі зміни, зроблені при проведенні.
        """
        for item in self.hardware_list:
            hardware_doc = frappe.get_doc("oiHardware", item.hardware)

            if hardware_doc.is_batched_asset:
                # Повертаємо кількість для партійних активів
                hardware_doc.quantity += item.quantity

            # Примітка: тут можна додати логіку видалення запису з історії
            # або додати новий запис "Повернення" для повноти аудиту.

            hardware_doc.save(ignore_permissions=True)

        self.db_set("status", "Скасовано")

    def _add_movement_log(self, hardware_doc, quantity):
        """
        Приватний метод для додавання запису в історію переміщень.
        """
        hardware_doc.append("movement_history", {
            "movement_date": self.transfer_date,
            "from_counterparty": self.from_partner,
            "to_counterparty": self.to_partner,
            "status": f"Передано ({quantity} од.)",
            "reference_document": self.name,
            "reference_doctype": self.doctype,
            "reference_name": self.name
        })
