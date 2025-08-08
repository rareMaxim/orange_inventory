# Copyright (c) 2025, Maxim Sysoev and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

# Допоміжні функції
# ----------------------------------------------------------------------


def _create_test_asset():
    """Створює актив для подальшого списання."""
    if frappe.db.exists("oiAsset", {"serial_no": "ASSET-TO-DECOM-001"}):
        return frappe.get_doc("oiAsset", {"serial_no": "ASSET-TO-DECOM-001"})

    asset = frappe.get_doc({
        "doctype": "oiAsset",
        "asset_name": "Старий Принтер",
        "status": "На складі",
        "quantity": 1,
        "cost": 500,
        "serial_no": "ASSET-TO-DECOM-001"
    })
    asset.insert()
    return asset


def create_decommissioning_act(asset_to_decommission_name):
    """Створює тестовий "Акт списання"."""
    if not frappe.db.exists("oiBasisDoc", {"title": "Рішення про Списання"}):
        frappe.get_doc({"doctype": "oiBasisDoc", "title": "Рішення про Списання",
                       "decision_number": "DEC-DECOM-789", "decision_date": nowdate()}).insert()

    decision = frappe.get_value(
        "oiBasisDoc", {"title": "Рішення про Списання"}, "name")

    act = frappe.get_doc({
        "doctype": "oiDecommissioningAct",
        "decommission_date": nowdate(),
        "decision": decision,
        "items": [
            {
                "asset": asset_to_decommission_name
            }
        ]
    })
    act.insert()
    return act


class IntegrationTestoiDecommissioningAct(IntegrationTestCase):
    """
    Integration tests for oiDecommissioningAct.
    Use this class for testing interactions between multiple components.
    """

    def tearDown(self):
        frappe.db.rollback()

    def test_asset_status_on_submit(self):
        """Тестує зміну статусу та кількості активу після списання."""
        # 1. Створюємо актив
        test_asset = _create_test_asset()

        # 2. Створюємо та затверджуємо акт списання
        decommissioning_act = create_decommissioning_act(test_asset.name)
        decommissioning_act.submit()

        # 3. Перевіряємо, що дані активу оновилися
        test_asset.reload()
        self.assertEqual(test_asset.status, "Списано")
        self.assertEqual(test_asset.quantity, 0)

        # 4. Перевіряємо історію руху
        self.assertEqual(len(test_asset.movement_history), 1)
        self.assertEqual(
            test_asset.movement_history[0].movement_type, "Списання")
