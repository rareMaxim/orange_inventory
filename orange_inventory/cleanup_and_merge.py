import frappe

from orange_inventory.agent_api.networking import _process_neighbors, _sync_network_ports


def run():
	asset_name = "pimkud8mh0"
	router_mac = "18:fd:74:39:d9:42"

	print("Pre-sync port count:", len(frappe.get_all("oiNetworkPort", filters={"asset": asset_name})))

	# Синхронізація (має спрацювати мерджинг)
	_sync_network_ports(
		asset_name,
		[
			{"name": "ether1", "mac_address": "18:fd:74:0e:4d:a0"},
			{"name": "wifi1", "mac_address": "18:fd:74:0e:4d:a2"},
		],
	)
	frappe.db.commit()

	print("Post-sync port count:", len(frappe.get_all("oiNetworkPort", filters={"asset": asset_name})))

	# Обробка сусідів
	_process_neighbors(
		"test-agent",
		asset_name,
		[
			{"mac_address": router_mac, "interface": "ether1"},
			{"mac_address": router_mac, "interface": "wifi1"},
		],
	)
	frappe.db.commit()

	# Результат
	ports = frappe.get_all(
		"oiNetworkPort",
		filters={"asset": asset_name, "port_name": ["in", ["Eth1", "ether1", "wifi1"]]},
		fields=["port_name", "connected_asset"],
	)
	for p in ports:
		print(f"Port {p.port_name}: connection -> {p.connected_asset}")


if __name__ == "__main__":
	run()
