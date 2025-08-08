# Copyright (c) 2025, Maxim Sysoev and Contributors
# See license.txt

import json

from orange_inventory.orange_inventory.doctype.oiasset.oiasset import split_asset

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

# Допоміжні функції
# ----------------------------------------------------------------------


def _create_group_asset():
    """Створює тестовий "груповий" актив для розділення."""
    if frappe.db.exists("oiAsset", {"asset_name": "Набір Кабелів HDMI"}):
        return frappe.get_doc("oiAsset", {"asset_name": "Набір Кабелів HDMI"})

    asset = frappe.get_doc({
        "doctype": "oiAsset",
        "asset_name": "Набір Кабелів HDMI",
        "status": "На складі",
        "quantity": 5,  # Груповий актив з 5 одиниць
        "cost": 150
    })
    asset.insert()
    return asset


class IntegrationTestoiAsset(IntegrationTestCase):
    """
    Integration tests for oiAsset.
    Use this class for testing interactions between multiple components.
    """

    def tearDown(self):
        frappe.db.rollback()

    def test_split_asset(self):
        """Тестує функціональність розділення групового активу."""
        # 1. Створюємо груповий актив
        source_asset = _create_group_asset()

        # 2. Готуємо список нових серійних номерів
        serial_numbers = ["HDMI-001", "HDMI-002",
                          "HDMI-003", "HDMI-004", "HDMI-005"]
        # Конвертуємо у JSON-рядок, як це робить фронтенд
        serial_numbers_json = json.dumps(serial_numbers)

        # 3. Викликаємо whitelisted-функцію
        split_asset(source_asset_name=source_asset.name,
                    serial_numbers=serial_numbers_json)

        # 4. Перевіряємо вихідний (тепер оновлений) актив
        source_asset.reload()
        self.assertEqual(source_asset.quantity, 1)
        self.assertEqual(source_asset.serial_no, "HDMI-001")
        # Перевіряємо, що в історію додався запис про розділення
        self.assertTrue(any(d.movement_type.startswith("Деталізація")
                        for d in source_asset.movement_history))

        # 5. Перевіряємо, що було створено 4 нових активи
        new_assets_count = frappe.db.count(
            "oiAsset", {"asset_name": "Набір Кабелів HDMI", "serial_no": ["!=", "HDMI-001"]})
        self.assertEqual(new_assets_count, 4)

        # 6. Перевіряємо один з нових активів
        new_asset = frappe.get_doc("oiAsset", {"serial_no": "HDMI-004"})
        self.assertEqual(new_asset.quantity, 1)
        self.assertEqual(new_asset.cost, 150)
