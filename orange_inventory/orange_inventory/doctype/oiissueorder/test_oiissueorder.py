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


def _create_prerequisites():
    """Створює базові записи, необхідні для тестів цього файлу."""
    # Створюємо дві організації для переміщення активів між ними
    if not frappe.db.exists("oiOrganization", "Тестова Організація-Відправник"):
        frappe.get_doc({"doctype": "oiOrganization",
                       "organization_name": "Тестова Організація-Відправник"}).insert()
    if not frappe.db.exists("oiOrganization", "Тестова Організація-Отримувач"):
        frappe.get_doc({"doctype": "oiOrganization",
                       "organization_name": "Тестова Організація-Отримувач"}).insert()

    # Створюємо інші необхідні записи
    if not frappe.db.exists("oiAssetType", {"asset_type_name": "Монітори"}):
        frappe.get_doc({"doctype": "oiAssetType",
                       "asset_type_name": "Монітори"}).insert()
    if not frappe.db.exists("oiBasisDoc", {"title": "Тестове Рішення для Передачі"}):
        frappe.get_doc({
            "doctype": "oiBasisDoc", "title": "Тестове Рішення для Передачі",
            "decision_number": "TEST-TRANSFER-456", "decision_date": nowdate()
        }).insert()


def _create_test_asset(owner_org_name, asset_name, qty, cost, serial_no=None):
    """Створює тестовий актив, який ми будемо передавати."""
    owner = frappe.get_value(
        "oiOrganization", {"organization_name": owner_org_name}, "name")
    asset_type = frappe.get_value(
        "oiAssetType", {"asset_type_name": "Монітори"}, "name")

    asset = frappe.get_doc({
        "doctype": "oiAsset",
        "asset_name": asset_name,
        "asset_type": asset_type,
        "current_owner": owner,
        "status": "На складі",
        "quantity": qty,
        "cost": cost,
        "serial_no": serial_no
    })
    asset.insert()
    return asset


def create_issue_order(from_org_name, to_org_name, asset_doc_name, qty_to_transfer):
    """Створює тестовий "Видатковий ордер"."""
    from_org = frappe.get_value(
        "oiOrganization", {"organization_name": from_org_name}, "name")
    to_org = frappe.get_value(
        "oiOrganization", {"organization_name": to_org_name}, "name")
    decision = frappe.get_value(
        "oiBasisDoc", {"title": "Тестове Рішення для Передачі"}, "name")

    issue_order = frappe.get_doc({
        "doctype": "oiIssueOrder",
        "issue_date": nowdate(),
        "decision": decision,
        "from_organization": from_org,
        "to_organization": to_org,
        "items": [
            {
                "asset": asset_doc_name,
                "qty": qty_to_transfer
            }
        ]
    })
    issue_order.insert()
    return issue_order


class IntegrationTestoiIssueOrder(IntegrationTestCase):
    """
    Integration tests for oiIssueOrder.
    Use this class for testing interactions between multiple components.
    """

    def setUp(self):
        _create_prerequisites()

    def tearDown(self):
        frappe.db.rollback()

    def test_full_transfer(self):
        """Тестує повну передачу одного активу (кількість 1)."""
        # 1. Створюємо актив, який будемо передавати
        source_asset = _create_test_asset(
            owner_org_name="Тестова Організація-Відправник",
            asset_name="Монітор LG 27'",
            qty=1, cost=12000, serial_no="LG-MON-001"
        )

        # 2. Створюємо та затверджуємо видатковий ордер
        issue_order = create_issue_order(
            from_org_name="Тестова Організація-Відправник",
            to_org_name="Тестова Організація-Отримувач",
            asset_doc_name=source_asset.name,
            qty_to_transfer=1
        )
        issue_order.submit()

        # 3. Перевіряємо, що власник активу змінився
        source_asset.reload()  # Оновлюємо дані з БД
        new_owner = frappe.get_value("oiOrganization", {
                                     "organization_name": "Тестова Організація-Отримувач"}, "name")

        self.assertEqual(source_asset.current_owner, new_owner)
        self.assertEqual(source_asset.status, "В експлуатації")
        self.assertEqual(len(source_asset.movement_history),
                         1)  # Перевіряємо історію
        self.assertEqual(
            source_asset.movement_history[0].movement_type, "Передача")

    def test_partial_transfer_split(self):
        """Тестує часткову передачу, яка має розділити актив."""
        # 1. Створюємо "груповий" актив (10 штук)
        source_asset = _create_test_asset(
            owner_org_name="Тестова Організація-Відправник",
            asset_name="USB-Хаб",
            qty=10, cost=500
        )

        # 2. Створюємо ордер на передачу 3 з 10 штук
        issue_order = create_issue_order(
            from_org_name="Тестова Організація-Відправник",
            to_org_name="Тестова Організація-Отримувач",
            asset_doc_name=source_asset.name,
            qty_to_transfer=3
        )
        issue_order.submit()

        # 3. Перевіряємо вихідний актив
        source_asset.reload()
        # Кількість має зменшитись до 7
        self.assertEqual(source_asset.quantity, 7)

        # 4. Перевіряємо, що був створений НОВИЙ актив
        new_asset_exists = frappe.db.exists(
            "oiAsset",
            {
                "asset_name": "USB-Хаб",
                "current_owner": frappe.get_value("oiOrganization", {"organization_name": "Тестова Організація-Отримувач"}),
                "quantity": 3
            }
        )
        self.assertTrue(new_asset_exists,
                        "Новий актив для отримувача не було створено")

    def test_validation_insufficient_quantity(self):
        """Тестує валідацію: не можна передати більше, ніж є."""
        # 1. Створюємо актив з кількістю 5
        source_asset = _create_test_asset(
            owner_org_name="Тестова Організація-Відправник",
            asset_name="Веб-камера",
            qty=5, cost=2000
        )

        # 2. Створюємо ордер на передачу 10 штук (неможлива операція)
        issue_order = create_issue_order(
            from_org_name="Тестова Організація-Відправник",
            to_org_name="Тестова Організація-Отримувач",
            asset_doc_name=source_asset.name,
            qty_to_transfer=10  # Намагаємось передати більше, ніж є
        )

        # 3. Перевіряємо, що система видасть помилку валідації
        with self.assertRaises(frappe.ValidationError):
            issue_order.save()  # Перевірка відбувається на етапі збереження/затвердження
