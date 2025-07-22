# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHardware(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_table.oiasset_table import oiAssetTable

        acquired_from: DF.Link | None
        acquisition_date: DF.Date | None
        acquisition_type: DF.Literal["\u041f\u043e\u043a\u0443\u043f\u043a\u0430", "\u041f\u043e\u0436\u0435\u0440\u0442\u0432\u0430", "\u041f\u0435\u0440\u0435\u0434\u0430\u0447\u0430"]
        asset_category: DF.Link
        asset_tag: DF.Data | None
        assets: DF.Table[oiAssetTable]
        company: DF.Link | None
        fin_resp_company: DF.Link | None
        fin_resp_deparnament: DF.Link | None
        fin_resp_user_name: DF.Link | None
        financially_responsible_person: DF.Link | None
        inventory_date: DF.Date | None
        item_name: DF.Data | None
        manufacturer: DF.Link | None
        model: DF.Link | None
        picture: DF.AttachImage | None
        purchase_cost: DF.Currency
        purchase_date: DF.Date | None
        quantity: DF.Float
        serial_number: DF.Data | None
        source_document: DF.Attach | None
        status: DF.Link | None
        title: DF.Data | None
        total_quantity: DF.Data | None
        type: DF.Link | None
        unit_cost: DF.Currency
        user: DF.Link | None
        user_name: DF.Link | None
    # end: auto-generated types

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
        serial_number = f"{hardware_doc.item_name}-{str(p_start_no + i).zfill(5)}"

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
