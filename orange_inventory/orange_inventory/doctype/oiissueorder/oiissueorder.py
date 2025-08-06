# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiIssueOrder(Document):
    def on_validate(self):
        """
        Перевіряє ключові умови перед збереженням 'Видаткового ордера'.
        """
        for item in self.items:
            if not item.asset:
                continue

            asset_data = frappe.db.get_value("oiAsset", item.asset, [
                                             "quantity", "current_owner", "asset_name"], as_dict=True)

            if not asset_data:
                frappe.throw(f"Актив {item.asset} не знайдено в системі.")

            if asset_data.quantity < item.qty:
                frappe.throw(
                    f"Для активу **{asset_data.asset_name} ({item.asset})**: недостатньо кількості. "
                    f"В наявності: {asset_data.quantity}, потрібно: {item.qty}"
                )

            if asset_data.current_owner != self.from_organization:
                owner_name = frappe.db.get_value(
                    "oiOrganization", asset_data.current_owner, "organization_name")
                frappe.throw(
                    f"Помилка передачі активу **{asset_data.asset_name} ({item.asset})**. "
                    f"Актив наразі належить **{owner_name}**, а не **{self.from_organization}**."
                )

    def on_submit(self):
        """
        При затвердженні 'Видаткового ордеру' оновлює активи та їх історію.
        Розрізняє повну передачу та розділення активу.
        """
        for item in self.items:
            source_asset = frappe.get_doc("oiAsset", item.asset)

            # --- СЦЕНАРІЙ 1: ПОВНА ПЕРЕДАЧА ---
            # Якщо ми передаємо всю наявну кількість, ми просто оновлюємо існуючий актив.
            if source_asset.quantity == item.qty:
                source_asset.current_owner = self.to_organization
                source_asset.responsible_employee = self.to_employee
                source_asset.status = "В експлуатації"

                source_asset.append("movement_history", {
                    "date": self.issue_date,
                    "movement_type": "Передача",
                    "from_source_type": "oiOrganization",
                    "from_source_name": self.from_organization,
                    "to_organization": self.to_organization,
                    "reference_appendix": self.decision
                })
                source_asset.save()

            # --- СЦЕНАРІЙ 2: ЧАСТКОВА ПЕРЕДАЧА (РОЗДІЛЕННЯ) ---
            # Якщо ми передаємо тільки частину.
            else:
                # Створюємо новий актив для переданої частини
                new_asset = frappe.copy_doc(source_asset)
                # ВАЖЛИВО: Очищаємо серійний номер, бо він залишається у вихідного активу.
                # Новий запис - це просто кількість без унікального серійника.
                new_asset.serial_no = None
                new_asset.quantity = item.qty
                new_asset.current_owner = self.to_organization
                new_asset.responsible_employee = self.to_employee
                new_asset.status = "В експлуатації"
                new_asset.movement_history = []  # Очищаємо скопійовану історію
                new_asset.insert(ignore_permissions=True,
                                 ignore_mandatory=True)

                new_asset.append("movement_history", {
                    "date": self.issue_date,
                    "movement_type": "Надходження (переміщення)",
                    "from_source_type": "oiOrganization",
                    "from_source_name": self.from_organization,
                    "to_organization": self.to_organization,
                    "reference_appendix": self.decision
                })
                new_asset.save()

                # Оновлюємо вихідний актив
                source_asset.quantity -= item.qty
                source_asset.append("movement_history", {
                    "date": self.issue_date,
                    "movement_type": f"Передача частини ({item.qty} од.)",
                    "to_organization": self.to_organization,
                    "reference_appendix": self.decision
                })
                source_asset.save()
