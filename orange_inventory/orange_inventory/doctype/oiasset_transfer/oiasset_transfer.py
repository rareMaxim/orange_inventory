# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAssetTransfer(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_transfer_item.oiasset_transfer_item import oiAssetTransferItem

        amended_from: DF.Link | None
        document_date: DF.Date
        document_number: DF.Data
        document_type: DF.Literal["\u0420\u0456\u0448\u0435\u043d\u043d\u044f",
                                  "\u041d\u0430\u043a\u0430\u0437", "\u0414\u043e\u0433\u043e\u0432\u0456\u0440"]
        hardware_list: DF.Table[oiAssetTransferItem]
        scan: DF.Attach | None
        title: DF.SmallText
        transfer_date: DF.Date | None
    # end: auto-generated types

    def on_submit(self):
        """
        Обробляє переміщення активів одразу після підтвердження документа.
        Оновлює статус та власника в картках oiHardware.
        """
        updated_assets = []
        # Перевіряємо, чи є що переміщувати
        if not self.hardware_list:
            frappe.throw("Додайте хоча б один актив для переміщення.")

        for item in self.hardware_list:
            if not item.hardware or not item.to_counterparty:
                frappe.throw(
                    "Для всіх рядків мають бути заповнені поля 'Актив' та 'Отримувач'.")

            try:
                hardware_doc = frappe.get_doc("oiHardware", item.hardware)
                # Зберігаємо поточного власника, щоб записати його в поле "Від кого"
                original_owner = hardware_doc.asset_owner
                original_status = hardware_doc.status
                # Оновлюємо ключові поля
                hardware_doc.asset_owner = item.to_counterparty
                # Встановлюємо статус "Експлуатується"
                hardware_doc.status = "Передано"

                # 👇 ДОДАНО: Створюємо запис в історії переміщень 👇
                hardware_doc.append("movement_history", {
                    "date": self.get("document_date") or frappe.utils.nowdate(),
                    "from_party": original_owner,
                    "to_party": item.to_counterparty,
                    "status": "Передано",
                    "document_type": self.doctype,
                    "document_name": self.name
                })
                # Логіка для партіонних активів
                if hardware_doc.is_batched:
                    if not item.quantity or item.quantity <= 0:
                        frappe.throw(
                            f"Для партіонного активу '{hardware_doc.title}' потрібно вказати кількість.")

                    if item.quantity > hardware_doc.quantity:
                        frappe.throw(
                            f"Недостатньо залишків для '{hardware_doc.title}'. В наявності: {hardware_doc.quantity}, потрібно: {item.quantity}")

                    if item.quantity < hardware_doc.quantity:
                        # Створюємо новий документ для частини, що переміщується
                        new_doc = frappe.copy_doc(hardware_doc)
                        new_doc.quantity = item.quantity
                        new_doc.asset_owner = item.to_counterparty
                        new_doc.financially_responsible_person = None
                        new_doc.status = "Передано"
                        new_doc.name = None  # Скидаємо ім'я для генерації нового
                        new_doc.insert(ignore_permissions=True)
                        updated_assets.append(new_doc.name)

                        # Зменшуємо кількість у вихідному документі
                        hardware_doc.quantity -= item.quantity
                        if hardware_doc.quantity > 0:
                            hardware_doc.status = original_status
                        hardware_doc.save(ignore_permissions=True)
                    else:
                        # Якщо переміщуємо всю партію, просто оновлюємо існуючий документ
                        hardware_doc.save(ignore_permissions=True)
                        updated_assets.append(hardware_doc.name)
                else:
                    # Якщо актив не партіонний, просто зберігаємо зміни
                    hardware_doc.save(ignore_permissions=True)
                    updated_assets.append(hardware_doc.name)

            except Exception as e:
                frappe.log_error(frappe.get_traceback(),
                                 "Помилка при переміщенні активу")
                # Скасовуємо транзакцію, щоб уникнути часткового оновлення
                frappe.db.rollback()
                frappe.throw(
                    f"Сталася помилка при оновленні активу {item.hardware}: {e}")

        # Оновлюємо статус самого документа переміщення
        frappe.msgprint(
            f"Успішно переміщено {len(updated_assets)} актив(и/ів).")

    @frappe.whitelist()
    def get_hardware_details(self):
        """
        Приймає список активів з документа та повертає словники 
        з деталями активів (вартість, категорія) та іменами контрагентів.
        """
        if not self.hardware_list:
            return {}

        # 1. Отримуємо деталі по активах
        hardware_names = [
            item.hardware for item in self.hardware_list if item.hardware]
        hardware_details_map = {}
        if hardware_names:
            # ВИПРАВЛЕНО: 'hardware_category' замінено на 'asset_category'
            details = frappe.get_all(
                "oiHardware",
                filters={"name": ["in", hardware_names]},
                fields=["name", "unit_cost", "asset_category"]
            )
            hardware_details_map = {d["name"]: d for d in details}

        # 2. Отримуємо повні імена контрагентів
        counterparty_ids = list(
            set(item.to_counterparty for item in self.hardware_list if item.to_counterparty))
        counterparty_names_map = {}
        if counterparty_ids:
            # ВИПРАВЛЕНО: Робимо запит, щоб отримати full_name для кожного контрагента
            names = frappe.get_all(
                "oiOrganisation Structure",
                filters={"name": ["in", counterparty_ids]},
                fields=["name", "full_name"]
            )
            counterparty_names_map = {n["name"]: n["full_name"] for n in names}

        return {
            "hardware_details": hardware_details_map,
            "counterparty_names": counterparty_names_map
        }
