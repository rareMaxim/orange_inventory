import json

import frappe
from frappe.tests import IntegrationTestCase

from orange_inventory.agent_api import report_machine_data


class TestAgentDiscovery(IntegrationTestCase):
	def setUp(self):
		# Ми НЕ видаляємо всі дані за допомогою frappe.db.delete,
		# бо це може пошкодити основну базу даних.
		# Замість цього ми створюємо активи з унікальними назвами для тестів.

		self.test_suffix = frappe.generate_hash(length=8)

		self.asset1 = frappe.get_doc(
			{
				"doctype": "oiAsset",
				"asset_name": f"Test-M1-{self.test_suffix}",
				"serial_no": f"SN-1-{self.test_suffix}",
			}
		).insert()

		self.asset2 = frappe.get_doc(
			{
				"doctype": "oiAsset",
				"asset_name": f"Test-M2-{self.test_suffix}",
				"serial_no": f"SN-2-{self.test_suffix}",
			}
		).insert()

		# Створюємо РОУТЕР (без агента, але з MAC)
		self.router = frappe.get_doc(
			{
				"doctype": "oiAsset",
				"asset_name": f"Test-Router-{self.test_suffix}",
				"mac_addresses": "00:99:88:77:66:55",  # MAC лишимо фіксованим для зручності тесту
				"is_network_device": 1,
			}
		).insert()

	def test_neighbor_discovery(self):
		# 1. Реєструємо Machine 2 (сусід)
		static_data2 = json.dumps(
			{
				"hostname": "machine2",
				"board_serial": "board2",
				"bios": {"serial_number": "SN-002"},
				"network_adapters": [{"name": "eth0", "mac_address": "00:11:22:33:44:55"}],
			}
		)
		# Це має створити oiNetworkPort для Machine 2 з вказаним MAC
		report_machine_data(static_data=static_data2)

		# Перевіряємо чи створився порт для Machine 2
		machine2_port = frappe.get_doc(
			"oiNetworkPort", {"asset": self.asset2.name, "mac_address": "00:11:22:33:44:55"}
		)
		self.assertEqual(machine2_port.port_name, "Auto-eth0")

		# 2. Дані від Machine 1, яка бачить і Machine 2, і РОУТЕР
		static_data1 = json.dumps(
			{
				"hostname": "machine1",
				"board_serial": "board1",
				"bios": {"serial_number": "SN-001"},
				"network_adapters": [{"name": "eth0", "mac_address": "00:aa:bb:cc:dd:ee"}],
			}
		)

		dynamic_data1 = json.dumps(
			{
				"neighbors": [
					{"ip_address": "192.168.1.2", "mac_address": "00:11:22:33:44:55", "interface": "eth0"},
					{"ip_address": "192.168.1.1", "mac_address": "00:99:88:77:66:55", "interface": "eth0"},
				]
			}
		)

		# Викликаємо API для Machine 1
		report_machine_data(static_data=static_data1, dynamic_data=dynamic_data1)

		# Перевіряємо зв'язок з Machine 2
		# Має створитися унікальний Auto-порт на Machine 1
		my_port_to_m2 = frappe.get_doc(
			"oiNetworkPort", {"asset": self.asset1.name, "port_name": "Auto-eth0-33:44:55"}
		)
		self.assertEqual(my_port_to_m2.connection, machine2_port.name)

		# Перевіряємо зв'язок з РОУТЕРОМ (через mac_addresses активу, бо порту немає)
		self.assertTrue(
			frappe.db.exists("oiNetworkPort", {"asset": self.router.name, "port_name": "Auto-Discovery"})
		)
		router_port = frappe.get_doc(
			"oiNetworkPort", {"asset": self.router.name, "port_name": "Auto-Discovery"}
		)
		self.assertEqual(router_port.mac_address, "00:99:88:77:66:55")

	def tearDown(self):
		# Видаляємо лише ті активи та пов'язані з ними дані, які ми створили в тесті
		assets_to_delete = []
		if hasattr(self, "asset1"):
			assets_to_delete.append(self.asset1.name)
		if hasattr(self, "asset2"):
			assets_to_delete.append(self.asset2.name)
		if hasattr(self, "router"):
			assets_to_delete.append(self.router.name)

		for asset_name in assets_to_delete:
			# 1. Видаляємо порти цього активу
			ports = frappe.get_all("oiNetworkPort", filters={"asset": asset_name})
			for p in ports:
				frappe.delete_doc("oiNetworkPort", p.name, force=True, ignore_permissions=True)

			# 2. Видаляємо агентів цього активу
			agents = frappe.get_all("oiAgent", filters={"asset": asset_name})
			for a in agents:
				frappe.delete_doc("oiAgent", a.name, force=True, ignore_permissions=True)

			# 3. Видаляємо сам актив
			frappe.delete_doc("oiAsset", asset_name, force=True, ignore_permissions=True)

		frappe.db.commit()
