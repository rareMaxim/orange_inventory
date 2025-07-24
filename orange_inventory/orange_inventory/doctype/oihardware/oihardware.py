# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

import datetime
import frappe
from frappe.model.document import Document


class oiHardware(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oihardware_movement_history.oihardware_movement_history import oiHardwareMovementHistory

        acquired_from: DF.Link | None
        acquisition_date: DF.Date | None
        acquisition_type: DF.Literal["\u041f\u043e\u043a\u0443\u043f\u043a\u0430", "\u041f\u043e\u0436\u0435\u0440\u0442\u0432\u0430", "\u041f\u0435\u0440\u0435\u0434\u0430\u0447\u0430"]
        asset_category: DF.Link
        asset_tag: DF.Data | None
        company: DF.Link | None
        financially_responsible_person: DF.Link | None
        inventory_date: DF.Date | None
        is_batched: DF.Check
        manufacturer: DF.Link | None
        model: DF.Link | None
        movement_history: DF.Table[oiHardwareMovementHistory]
        picture: DF.AttachImage | None
        purchase_cost: DF.Currency
        purchase_date: DF.Date | None
        quantity: DF.Float
        serial_number: DF.Data | None
        source_document: DF.Attach | None
        status: DF.Link | None
        title: DF.Data | None
        total_cost: DF.Currency
        type: DF.Link | None
        unit_cost: DF.Currency
        user: DF.Link | None
    # end: auto-generated types

    @frappe.whitelist()
    def refresh_movement_history(self):
        """
        Очищує та заново заповнює дочірню таблицю `movement_history`,
        використовуючи коректний синтаксис фільтрації для дочірніх таблиць.
        """

        self.set("movement_history", [])

        # --- Крок 1: Акти Прийому ---
        # Використовуємо синтаксис [Child_DocType, field, operator, value]
        acceptance_docs = frappe.get_all(
            "oiAsset Acceptance",
            filters=[
                ["oiAsset Acceptance Item", "item_name", "=", self.title],
                ["docstatus", "=", 1]  # Враховуємо тільки підтверджені документи
            ],
            fields=["name", "posting_date", "counterparty"]
        )
        for item in acceptance_docs:
            self.append("movement_history", {
                "date": item.posting_date,
                "document_type": "oiAsset Acceptance",
                "document_name": item.name,
                "to_party": item.counterparty
            })

        # --- Крок 2: Акти Переміщення ---
        transfer_docs = frappe.get_all(
            "oiAsset Transfer",
            filters=[
                ["oiAsset Transfer Item", "hardware", "=", self.name],
                ["docstatus", "=", 1]  # Враховуємо тільки підтверджені документи
            ],
            fields=["name", "transfer_date",
                    "from_counterparty", "to_counterparty"]
        )
        for item in transfer_docs:
            self.append("movement_history", {
                "date": item.transfer_date,
                "document_type": "oiAsset Transfer",
                "document_name": item.name,
                "from_party": item.from_counterparty,
                "to_party": item.to_counterparty
            })

        # --- Крок 3: Сортування історії за датою ---
        # Переконуємося, що дати існують, щоб уникнути помилок при сортуванні
        self.movement_history = sorted(
            self.movement_history,
            key=lambda row: row.get("date") or datetime.date(1970, 1, 1)
        )

        # --- Крок 4: Збереження документа ---
        self.save()

        return "Історія переміщень успішно оновлена."


@frappe.whitelist()
def create_batch_assets(hardware_doc_name, qty, start_no):
    """
    Створює N документів oiAsset Item.
    Ця функція є точкою входу для клієнтського скрипту.

    :param hardware_doc_name: Назва документа oiHardware, до якого прив'язуємо активи.
    :param qty: Кількість активів для створення (рядок).
    :param start_no: Початковий номер для генерації серійників (рядок).
    """
    # Явно перетворюємо рядки в числа
    try:
        p_qty = int(qty)
        p_start_no = int(start_no)
    except (ValueError, TypeError):
        frappe.throw("Кількість та початковий номер мають бути числами.")

    # Завантажуємо батьківський документ
    hardware_doc = frappe.get_doc("oiHardware", hardware_doc_name)

    # Очищуємо таблицю перед додаванням нових
    hardware_doc.set("assets", [])

    for i in range(p_qty):
        serial_number = f"{hardware_doc.asset_tag}-{str(p_start_no + i).zfill(5)}"

        if frappe.db.exists("oiAsset Item", {"serial_no": serial_number}):
            continue

        # Створюємо новий документ oiAsset Item
        new_asset = frappe.get_doc({
            "doctype": "oiAsset Item",
            "hardware_type": hardware_doc.name,
            "serial_no": serial_number,
            "status": "На складі"
        })
        new_asset.insert(ignore_permissions=True)

        # Додаємо посилання на щойно створений актив у таблицю
        hardware_doc.append("assets", {
            "asset_item": new_asset.name
        })

    # Зберігаємо зміни в батьківському документі
    hardware_doc.save(ignore_permissions=True)

    # Повертаємо повідомлення про успіх (не обов'язково, але корисно для відладки)
    return f"Успішно створено {p_qty} активів."


@frappe.whitelist()
def update_asset_item_fields(asset_item_name, field_data):
    """
    Універсальний метод для оновлення полів в документі oiAsset Item.
    Приймає назву документа та словник з полями для оновлення.

    :param asset_item_name: Назва (ID) документа oiAsset Item.
    :param field_data: JSON-рядок словника, наприклад: '{"status": "В ремонті"}'
    """
    import json

    if not asset_item_name or not field_data:
        return

    try:
        data_to_update = json.loads(field_data)
        # Оновлюємо значення вказаних полів
        frappe.db.set_value("oiAsset Item", asset_item_name, data_to_update)
        # Повертаємо успішний статус для відладки
        return {"status": "success"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Asset Item Update Failed")
        frappe.throw(f"Не вдалося оновити актив: {e}")


@frappe.whitelist()
def update_asset_item_fields(asset_item_name, field_data):
    """
    Універсальний метод для оновлення полів в документі oiAsset Item.
    Приймає назву документа та словник з полями для оновлення.

    :param asset_item_name: Назва (ID) документа oiAsset Item.
    :param field_data: JSON-рядок словника, наприклад: '{"status": "В ремонті"}'
    """
    import json

    if not asset_item_name or not field_data:
        return

    try:
        data_to_update = json.loads(field_data)
        # Оновлюємо значення вказаних полів
        frappe.db.set_value("oiAsset Item", asset_item_name, data_to_update)
        # Повертаємо успішний статус для відладки
        return {"status": "success"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Asset Item Update Failed")
        frappe.throw(f"Не вдалося оновити актив: {e}")


@frappe.whitelist()
def link_assets(parent_doc_name, asset_item_list):
    """
    Прив'язує список обраних oiAsset Item до інвентарної картки oiHardware.
    """
    if isinstance(asset_item_list, str):
        import json
        asset_item_list = json.loads(asset_item_list)

    for asset_name in asset_item_list:
        # Оновлюємо поле 'inventory_card' в кожному обраному активі
        frappe.db.set_value("oiAsset Item", asset_name,
                            "inventory_card", parent_doc_name)

        # Додаємо посилання в таблицю 'assets' всередині oiHardware
        parent_doc = frappe.get_doc("oiHardware", parent_doc_name)
        parent_doc.append("assets", {
            "asset_item": asset_name
        })
        parent_doc.save(ignore_permissions=True)
