# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiReceiptOrder(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oireceiptorderitem.oireceiptorderitem import oiReceiptOrderItem

        amended_from: DF.Link | None
        decision: DF.Link
        items: DF.Table[oiReceiptOrderItem]
        receipt_date: DF.Date
        source_name: DF.DynamicLink | None
        source_project: DF.Link | None
        source_type: DF.Literal["oiDonor", "oiOrganization"]
        to_organization: DF.Link | None
    # end: auto-generated types

    def on_submit(self):
        """
        При затвердженні 'Прибуткового ордеру' створює записи в 'oiAsset'.
        """
        for item in self.items:
            # Обробка серійних номерів: перетворюємо рядок на список, видаляючи пробіли
            serial_numbers = []
            if item.serial_numbers:
                processed_string = item.serial_numbers.replace('\n', ',')
                serial_numbers = [s.strip()
                                  for s in processed_string.split(',') if s.strip()]

            # Якщо кількість > 1 і серійних номерів не вистачає, створюємо один "груповий" актив
            if item.qty > 1 and len(serial_numbers) != item.qty:
                self.create_single_asset(item, item.qty, item.serial_numbers)

            # Якщо кількість = 1 або кількість серійних номерів відповідає кількості активів
            else:
                if item.qty == 1:
                    # Створюємо один актив, навіть якщо серійних номерів немає
                    serial = serial_numbers[0] if serial_numbers else None
                    self.create_single_asset(item, 1, serial)
                else:
                    # Створюємо декілька активів, по одному на кожен серійний номер
                    for sn in serial_numbers:
                        self.create_single_asset(item, 1, sn)

    def create_single_asset(self, item, qty, serial_no):
        """
        Допоміжна функція для створення одного запису 'oiAsset'.
        """
        # Створюємо новий документ 'oiAsset' в пам'яті
        new_asset = frappe.new_doc("oiAsset")

        # Переносимо дані з ордеру в актив
        new_asset.asset_name = item.asset_name
        # new_asset.asset_model = item.asset_model
        new_asset.asset_type = item.asset_type
        new_asset.quantity = qty
        new_asset.cost = item.rate
        new_asset.serial_no = serial_no
        new_asset.status = "На складі"  # Початковий статус

        # Переносимо дані з "шапки" ордеру
        new_asset.acquisition_date = self.receipt_date
        new_asset.current_owner = self.to_organization
        new_asset.source_project = self.source_project

        # Обробка динамічного посилання на джерело
        if self.source_type == "oiDonor":
            new_asset.original_donor = self.source_name

        # Вставляємо новий документ в базу даних
        new_asset.insert()

        # Створюємо словник з даними для історії
        movement_data = {
            "date": self.receipt_date,
            "movement_type": "Надходження",
            "to_organization": self.to_organization,
            "reference_appendix": self.decision,
            # Встановлюємо тип джерела та саме джерело
            "from_source_type": self.source_type,
            "from_source_name": self.source_name
        }
        # Якщо джерело - це інша організація, фіксуємо це в полі "from_organization"
        if self.source_type == "oiOrganization":
            movement_data["from_organization"] = self.source_name

        # Додаємо запис в історію
        new_asset.append("movement_history", movement_data)

        # Зберігаємо зміни в історії
        new_asset.save()
