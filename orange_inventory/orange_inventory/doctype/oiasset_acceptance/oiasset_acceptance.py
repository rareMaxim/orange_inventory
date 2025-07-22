# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAssetAcceptance(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_acceptance_item.oiasset_acceptance_item import oiAssetAcceptanceItem

        amended_from: DF.Link | None
        basis_doc_no: DF.Data | None
        category_totals: DF.TextEditor | None
        counterparty: DF.Link | None
        items: DF.Table[oiAssetAcceptanceItem]
        posting_date: DF.Date | None
        total_amount: DF.Currency
    # end: auto-generated types

    def on_submit(self):
        # Проходимо по кожному рядку в "Акті Прийому"
        for item in self.items:
            if item.is_batched:
                # --- ЛОГІКА ДЛЯ ПАРТІОННИХ АКТИВІВ ---
                # Створюємо ОДНУ картку oiHardware
                new_hardware = frappe.get_doc({
                    "doctype": "oiHardware",
                    "title": item.item_name,
                    "is_batched": 1,
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                    "asset_category": item.asset_category,
                    "owner": self.counterparty  # Встановлюємо початкового власника
                })
                new_hardware.insert(ignore_permissions=True)
            else:
                # --- ЛОГІКА ДЛЯ ПОШТУЧНИХ (СЕРІЙНИХ) АКТИВІВ ---
                # Отримуємо список серійних номерів з текстового поля
                serial_no_list = [
                    s.strip() for s in item.serial_numbers.split('\n') if s.strip()]

                # Перевіряємо, чи кількість співпадає
                if len(serial_no_list) != item.quantity:
                    frappe.throw(f"Для '{item.item_name}' кількість ({item.quantity}) "
                                 f"не співпадає з кількістю серійних номерів ({len(serial_no_list)}).")

                # Створюємо ОКРЕМУ картку oiHardware для КОЖНОГО серійного номера
                for serial in serial_no_list:
                    if frappe.db.exists("oiHardware", {"serial_no": serial}):
                        continue  # Пропускаємо, якщо такий серійник вже є

                    new_hardware = frappe.get_doc({
                        "doctype": "oiHardware",
                        "title": item.item_name,
                        "is_batched": 0,
                        "quantity": 1,
                        "serial_no": serial,
                        "unit_cost": item.unit_cost,
                        "asset_category": item.asset_category,
                        "owner": self.counterparty
                    })
                    new_hardware.insert(ignore_permissions=True)
