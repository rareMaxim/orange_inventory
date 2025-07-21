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
        status: DF.Data | None
        to_counterparty: DF.Link
        transfer_date: DF.Date
        обладнання: DF.Table[oiHardwareTransferItem]
    # end: auto-generated types

    def on_submit(self):
        """
        Спрацьовує при проведенні (Submit) документа.
        Обробляє кожну позицію в списку обладнання:
        - Для партійних активів: зменшує кількість на складі.
        - Для унікальних активів: змінює відповідального/власника.
        - Для всіх: додає запис в історію переміщень.
        """
        for item in self.hardware_list:
            # Завантажуємо документ обладнання, що передається
            hardware_doc = frappe.get_doc("oiHardware", item.hardware)

            # --- Нова логіка для обробки кількості ---
            if hardware_doc.is_batched_asset:
                # Це партійний актив. Перевіряємо залишок і зменшуємо його.
                if hardware_doc.quantity < item.quantity:
                    frappe.throw(f"Недостатньо залишків для {hardware_doc.name}. "
                                 f"На складі: {hardware_doc.quantity}, "
                                 f"Спроба передати: {item.quantity}")

                hardware_doc.quantity -= item.quantity
            else:
                # Це унікальний, серіалізований актив.
                # Можна додати логіку зміни власника або статусу, якщо потрібно.
                # Наприклад, можна змінити поле 'current_owner', якщо ви його додали.
                # hardware_doc.current_owner = self.to_partner
                pass  # Наразі просто фіксуємо рух

            # Додаємо запис в історію переміщень для всіх типів активів
            self.add_movement_log(hardware_doc, item.quantity)

            # Зберігаємо оновлений документ обладнання
            hardware_doc.save(ignore_permissions=True)

        # Оновлюємо статус самого документа StockTransfer
        self.db_set("status", "Завершено")

    def add_movement_log(self, hardware_doc, quantity):
        """
        Допоміжна функція для додавання запису в історію переміщень.
        """
        new_log_entry = hardware_doc.append("movement_history", {})

        # Заповнюємо поля нового запису в історії
        new_log_entry.movement_date = self.transfer_date
        new_log_entry.from_counterparty = self.from_partner
        new_log_entry.to_counterparty = self.to_partner

        # Створюємо інформативний статус
        status_text = f"Передано ({quantity} од.)"
        new_log_entry.status = status_text

        # Додаємо посилання на цей документ StockTransfer
        new_log_entry.reference_document = self.name
        new_log_entry.reference_doctype = self.doctype
        new_log_entry.reference_name = self.name

    def before_cancel(self):
        """
        Спрацьовує при скасуванні (Cancel) документа.
        Відкочує всі зміни, зроблені при проведенні.
        """
        for item in self.hardware_list:
            hardware_doc = frappe.get_doc("oiHardware", item.hardware)

            if hardware_doc.is_batched_asset:
                # Повертаємо кількість для партійних активів
                hardware_doc.quantity += item.quantity

            # Видаляємо відповідний запис з історії переміщень
            # Це більш складна логіка, яку можна додати пізніше,
            # щоб уникнути помилок при скасуванні кількох документів

            hardware_doc.save(ignore_permissions=True)

        self.db_set("status", "Скасовано")
