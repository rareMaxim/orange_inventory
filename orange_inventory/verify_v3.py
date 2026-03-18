import frappe

from orange_inventory.agent_api.snmp import _process_snmp_reports


def verify():
	# Дані для симуляції
	agent_name = "DESKTOP-46EJEE1-0a9251ad"
	router_asset = "6jcbm5dp7h"
	ap_asset = "pimkud8mh0"
	router_mac = "18:fd:74:39:d9:42"  # Одна з MAC-адрес роутера

	print(f"Verifying mapping for {ap_asset} to {router_asset}...")

	# Очищаємо всі зв'язки для чистого тесту
	frappe.db.set_value(
		"oiNetworkPort",
		{"asset": ap_asset},
		{"connection": None, "connected_asset": None},
		update_modified=False,
	)
	frappe.db.commit()

	# Симулюємо звіт з інтерфейсами (для запуску мерджингу) та сусідами
	mock_reports = [
		{
			"asset_name": ap_asset,
			"ip": "192.168.33.170",
			"interfaces": [
				{"name": "ether1", "mac": "18:fd:74:0e:4d:a0", "status": 1},
				{"name": "wifi1", "mac": "18:fd:74:0e:4d:a2", "status": 1},
			],
			"neighbors": [
				{"mac_address": router_mac, "interface": "ether1"},
				{"mac_address": router_mac, "interface": "wifi1"},
			],
		}
	]

	_process_snmp_reports(agent_name, mock_reports)
	frappe.db.commit()

	# Перевірка
	eth1_conn = frappe.db.get_value(
		"oiNetworkPort", {"asset": ap_asset, "port_name": "Eth1"}, ["connected_asset", "connection"]
	)
	wifi1_conn = frappe.db.get_value(
		"oiNetworkPort", {"asset": ap_asset, "port_name": "wifi1"}, ["connected_asset", "connection"]
	)

	print(f"Eth1 connection: {eth1_conn}")
	print(f"wifi1 connection: {wifi1_conn}")

	if eth1_conn and eth1_conn[0] == router_asset:
		print("SUCCESS: Connection correctly mapped to Eth1")
	else:
		print("FAILURE: Connection not mapped to Eth1")

	if wifi1_conn and wifi1_conn[0] == router_asset:
		print("FAILURE: Connection still exists on wifi1")
	else:
		print("SUCCESS: Connection correctly skipped on wifi1 (or wasn't there)")


if __name__ == "__main__":
	verify()
