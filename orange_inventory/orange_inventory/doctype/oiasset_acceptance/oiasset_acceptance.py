# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import fmt_money


class oiAssetAcceptance(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_acceptance_item.oiasset_acceptance_item import oiAssetAcceptanceItem

        amended_from: DF.Link | None
        asset_owner: DF.Link
        basis_doc_no: DF.Data
        category_totals: DF.TextEditor | None
        counterparty: DF.Link
        items: DF.Table[oiAssetAcceptanceItem]
        posting_date: DF.Date
        total_amount: DF.Currency
        total_quantity: DF.Int
    # end: auto-generated types

    def on_submit(self):
        for item in self.items:
            # Обробка товарів, що обліковуються партіями
            if item.is_batched:
                hw = frappe.new_doc('oiHardware')
                hw.title = item.item_name
                hw.item_name = item.item_name
                hw.is_batched = 1
                hw.asset_category = item.asset_category
                hw.unit_cost = item.unit_cost
                hw.quantity = item.quantity
                hw.total_cost = item.unit_cost * item.quantity
                hw.owner = self.asset_owner
                hw.acquisition_date = self.posting_date
                hw.acceptance_doc = self.name
                # Add a record to the movement history table
                hw.append("movement_history", {
                    "date": self.posting_date,
                    "document_type": "oiAsset Acceptance",
                    "document_name": self.name,
                    "from_party": self.counterparty,
                    "to_party": self.asset_owner
                })
                hw.insert()
                hw.save()
            else:
                # Обробка серіалізованих товарів
                serial_no_list = []
                if item.serial_numbers:
                    serial_no_list = [
                        s.strip() for s in item.serial_numbers.split('\n') if s.strip()
                    ]

                if not serial_no_list:
                    frappe.throw(
                        f"Для товару '{item.item_name}' не вказано серійні номери.")

                if len(serial_no_list) != item.quantity:
                    frappe.throw(
                        f"Кількість серійних номерів ({len(serial_no_list)}) "
                        f"не відповідає кількості товару ({item.quantity}) "
                        f"для '{item.item_name}'."
                    )

                for serial_no in serial_no_list:
                    hw = frappe.new_doc('oiHardware')
                    hw.title = item.item_name
                    hw.item_name = item.item_name
                    hw.is_batched = 0
                    hw.asset_category = item.asset_category
                    hw.unit_cost = item.unit_cost
                    hw.quantity = 1
                    hw.total_cost = item.unit_cost * hw.quantity
                    hw.serial_number = serial_no
                    hw.owner = self.asset_owner
                    hw.acquisition_date = self.posting_date
                    hw.acceptance_doc = self.name

                    # Add a record to the movement history table
                    hw.append("movement_history", {
                        "date": self.posting_date,
                        "document_type": "oiAsset Acceptance",
                        "document_name": self.name,
                        "from_party": self.counterparty,
                        "to_party": self.asset_owner
                    })
                    hw.insert()
                    hw.save()

    @frappe.whitelist()
    def calculate_category_totals(self):
        """
        Calculates total quantity and cost for each asset category based on the items table.
        The result is formatted as an HTML table and stored in the 'category_totals' field.
        """
        category_data = {}
        # Переконайтеся, що у вас є таблиця 'items'
        if not self.items:
            self.category_totals = "<p>Немає товарів для розрахунку.</p>"
            return

        for item in self.items:
            if item.asset_category:
                # Ініціалізація категорії, якщо її ще немає у словнику
                category_data.setdefault(item.asset_category, {
                                         'total_cost': 0, 'total_quantity': 0})

                # Агрегація вартості та кількості
                cost = (item.unit_cost or 0) * (item.quantity or 0)
                category_data[item.asset_category]['total_cost'] += cost
                category_data[item.asset_category]['total_quantity'] += (
                    item.quantity or 0)

        # Форматування виводу у вигляді HTML-таблиці
        html = """
			<table class="table table-bordered" style="font-size: 1rem;">
				<thead>
					<tr>
						<th>Категорія</th>
						<th style="width: 30%;">Загальна кількість</th>
						<th style="width: 35%;">Загальна вартість</th>
					</tr>
				</thead>
				<tbody>
		"""

        if not category_data:
            html += "<tr><td colspan='3' class='text-center'>Немає даних для відображення</td></tr>"
        else:
            for category, data in sorted(category_data.items()):
                formatted_cost = fmt_money(
                    data.get('total_cost', 0))
                html += f"""
					<tr>
						<td>{category}</td>
						<td>{data.get('total_quantity', 0)}</td>
						<td>{formatted_cost}</td>
					</tr>
				"""

        html += "</tbody></table>"

        # Оновлення поля в документі
        self.category_totals = html
        # Метод може повертати значення для прямого оновлення на клієнті, але оновлення поля є більш надійним
        return html
