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


# Допоміжні функції тепер знаходяться в одному файлі з тестом
# ----------------------------------------------------------------------

def _create_prerequisites():
    """Створює базові записи, необхідні для тестів цього файлу."""
    if not frappe.db.exists("oiOrganization", {"organization_name": "Тестова Організація 1"}):
        frappe.get_doc({
            "doctype": "oiOrganization",
            "organization_name": "Тестова Організація 1",
        }).insert()

    if not frappe.db.exists("oiAssetType", {"asset_type_name": "Ноутбуки"}):
        frappe.get_doc({
            "doctype": "oiAssetType",
            "asset_type_name": "Ноутбуки"
        }).insert()

    if not frappe.db.exists("oiBasisDoc", {"title": "Тестове Рішення для Тестів"}):
        frappe.get_doc({
            "doctype": "oiBasisDoc",
            "title": "Тестове Рішення для Тестів",
            "decision_number": "123-TEST",
            "decision_date": nowdate(),
            "basis_doc_type": "Рішення"
        }).insert()


def create_receipt_order(**kwargs):
    """Створює тестовий "Прибутковий ордер"."""
    organization = frappe.get_value(
        "oiOrganization", {"organization_name": "Тестова Організація 1"}, "name")
    asset_type = frappe.get_value(
        "oiAssetType", {"asset_type_name": "Ноутбуки"}, "name")
    decision = frappe.get_value(
        "oiBasisDoc", {"title": "Тестове Рішення для Тестів"}, "name")

    order_details = {
        "doctype": "oiReceiptOrder",
        "receipt_date": nowdate(),
        "decision": decision,
        "source_type": "oiDonor",
        "source_name": "Тестовий Донор",
        "to_organization": organization,
        "items": [
            {
                "asset_name": "Ноутбук Dell XPS 15",
                "asset_type": asset_type,
                "qty": 1,
                "rate": 55000,
                "serial_numbers": "TEST-SN-12345"
            }
        ]
    }
    order_details.update(kwargs)

    order = frappe.get_doc(order_details)
    order.insert()
    return order


class IntegrationTestoiReceiptOrder(IntegrationTestCase):
    """
    Integration tests for oiReceiptOrder.
    Use this class for testing interactions between multiple components.
    """

    def setUp(self):
        """Ця функція виконується перед кожним тестом."""
        # Створюємо базові записи, які можуть знадобитися
        _create_prerequisites()

    # ---> ДОДАЙТЕ ЦЕЙ МЕТОД <---
    def tearDown(self):
        """
        Ця функція виконується ПІСЛЯ кожного тесту.
        Відкочує всі зміни, зроблені в базі даних під час тесту.
        Це гарантує, що тести не впливають один на одного.
        """
        frappe.db.rollback()
    # -----------------------------

    def test_asset_creation_on_submit(self):
        """Тестує створення одного активу при затвердженні ордеру."""
        receipt_order = create_receipt_order()
        receipt_order.submit()

        self.assertTrue(frappe.db.exists(
            "oiAsset", {"serial_no": "TEST-SN-12345"}))
        created_asset = frappe.get_doc(
            "oiAsset", {"serial_no": "TEST-SN-12345"})

        self.assertEqual(created_asset.quantity, 1)
        self.assertEqual(created_asset.cost, 55000)
        self.assertEqual(created_asset.status, "На складі")

    def test_group_asset_creation(self):
        """
        Тестує створення одного "групового" активу, коли кількість > 1,
        але серійні номери не вказані.
        """
        receipt_order = create_receipt_order(items=[{
            "asset_name": "Комплект: Мишка + Клавіатура",
            "asset_type": frappe.get_value("oiAssetType", {"asset_type_name": "Ноутбуки"}),
            "qty": 10,
            "rate": 1500,
            "serial_numbers": ""  # Серійні номери не вказані
        }])
        receipt_order.submit()

        # Перевіряємо, що був створений ОДИН актив з кількістю 10
        self.assertTrue(frappe.db.exists(
            "oiAsset", {"asset_name": "Комплект: Мишка + Клавіатура"}))

        created_asset = frappe.get_doc(
            "oiAsset", {"asset_name": "Комплект: Мишка + Клавіатура"})
        self.assertEqual(created_asset.quantity, 10)
        # Перевіряємо, що серійний номер порожній
        self.assertIsNone(created_asset.serial_no)

    def test_multiple_assets_creation_with_serials(self):
        """
        Тестує створення кількох окремих активів, коли кількість
        співпадає з кількістю серійних номерів.
        """
        receipt_order = create_receipt_order(items=[{
            "asset_name": "Телефон Samsung Galaxy",
            "asset_type": frappe.get_value("oiAssetType", {"asset_type_name": "Ноутбуки"}),
            "qty": 3,
            "rate": 25000,
            # Вказуємо 3 серійні номери через кому
            "serial_numbers": "SAMSUNG-001, SAMSUNG-002, SAMSUNG-003"
        }])
        receipt_order.submit()

        # Перевіряємо, що було створено ТРИ окремі активи
        # 1. Рахуємо кількість документів
        assets_count = frappe.db.count(
            "oiAsset", {"asset_name": "Телефон Samsung Galaxy"})
        self.assertEqual(assets_count, 3)

        # 2. Перевіряємо наявність кожного активу за серійним номером
        self.assertTrue(frappe.db.exists(
            "oiAsset", {"serial_no": "SAMSUNG-001"}))
        self.assertTrue(frappe.db.exists(
            "oiAsset", {"serial_no": "SAMSUNG-002"}))
        self.assertTrue(frappe.db.exists(
            "oiAsset", {"serial_no": "SAMSUNG-003"}))

        # 3. Перевіряємо, що кожен з них має кількість = 1
        asset2 = frappe.get_doc("oiAsset", {"serial_no": "SAMSUNG-002"})
        self.assertEqual(asset2.quantity, 1)


# Допоміжна функція залишається без змін
def create_receipt_order(**kwargs):
    """Допоміжна функція для створення тестового "Прибуткового ордеру"."""

    organization = frappe.get_value(
        "oiOrganization", {"organization_name": "Тестова Організація 1"}, "name")
    asset_type = frappe.get_value(
        "oiAssetType", {"asset_type_name": "Ноутбуки"}, "name")
    decision = frappe.get_value(
        "oiBasisDoc", {"title": "Тестове Рішення для Тестів"}, "name")

    order = frappe.get_doc({
        "doctype": "oiReceiptOrder",
        "receipt_date": "2025-08-07",
        "decision": decision,
        "source_type": "oiDonor",
        "source_name": "Тестовий Донор",
        "to_organization": organization,
        "items": [
            {
                "asset_name": "Ноутбук Dell XPS 15",
                "asset_type": asset_type,
                "qty": 1,
                "rate": 55000,
                "serial_numbers": "TEST-SN-12345"
            }
        ]
    })

    order.update(kwargs)
    order.insert()
    return order
