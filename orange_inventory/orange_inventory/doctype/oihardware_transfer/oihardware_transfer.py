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
        for item in self.hardware_list:
            # Завантажуємо документ конкретної одиниці активу
            asset_item_doc = frappe.get_doc("Asset Item", item.asset_item)

            if asset_item_doc.status != 'На складі':
                frappe.throw(
                    f"Актив {asset_item_doc.serial_no} не знаходиться на складі.")

            # Оновлюємо статус та власника-контрагента
            asset_item_doc.status = 'В експлуатації'
            asset_item_doc.current_owner = self.to_counterparty

            # --- НОВА ЛОГІКА ---
            # Оновлюємо МВО та Користувача, ЯКЩО вони вказані в акті
            if item.new_responsible_person:
                asset_item_doc.responsible_person = item.new_responsible_person
            if item.new_asset_user:
                asset_item_doc.asset_user = item.new_asset_user

            asset_item_doc.save(ignore_permissions=True)

        self.db_set("status", "Завершено")

    def on_cancel(self):
        for item in self.hardware_list:
            asset_item_doc = frappe.get_doc("Asset Item", item.asset_item)

            asset_item_doc.status = 'На складі'
            asset_item_doc.current_owner = self.from_counterparty
            # При скасуванні МВО та користувач залишаються ті, що були призначені,
            # оскільки система не знає, хто був до цього.

            asset_item_doc.save(ignore_permissions=True)

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


@frappe.whitelist()
def update_hardware_category(hardware_name, new_category):
    """
    Дозволяє оновити категорію для вказаного обладнання.
    Цей метод можна викликати з клієнтського скрипту.

    :param hardware_name: ID (назва) документа oiHardware, який потрібно оновити.
    :param new_category: Нова категорія, яку потрібно встановити.
    """
    try:
        # Оновлюємо поле 'asset_category' в документі 'oiHardware'
        frappe.db.set_value("oiHardware", hardware_name,
                            "asset_category", new_category)
        return {"status": "success", "message": f"Category for {hardware_name} updated."}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         "Update Hardware Category Failed")
        # Повертаємо помилку на клієнт
        frappe.throw(f"Не вдалося оновити категорію: {e}")
