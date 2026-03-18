import frappe


@frappe.whitelist()
def get_topology_data():
	"""
	Повертає дані вузлів та зв'язків для побудови карти мережі.
	Вузли - це активи (oiAsset).
	Зв'язки формуються на основі підключень oiNetworkPort до інших активів.
	"""
	nodes = []
	edges = []

	# Спочатку отримуємо ID всіх активів, які мають хоча б один мережевий порт
	assets_with_ports = frappe.get_all("oiNetworkPort", pluck="asset", distinct=True)

	if not assets_with_ports:
		return {"nodes": [], "edges": []}

	# Отримуємо тільки ті активи, які теоретично можуть бути підключені до мережі
	assets = frappe.get_all(
		"oiAsset",
		filters={"name": ["in", assets_with_ports]},
		fields=[
			"name",
			"asset_name",
			"ip_address",
			"mac_addresses",
			"status",
			"is_network_device",
			"manufacturer",
		],
	)

	asset_map = {a.name: a for a in assets}

	added_edges = set()

	for asset in assets:
		# Вибір іконки за типом
		icon = "\uf108"  # fa-desktop
		group = "computer"

		# Якщо це мережеве обладнання
		if asset.is_network_device:
			if asset.manufacturer and "MikroTik" in asset.manufacturer:
				icon = "\uf233"  # fa-server (router/switch)
				group = "router"
			else:
				icon = "\uf6ff"  # fa-network-wired
				group = "switch"

		title = f"<b>{asset.asset_name or asset.name}</b><br>IP: {asset.ip_address or 'N/A'}<br>MAC: {asset.mac_addresses or 'N/A'}<br>Статус: {asset.status}"

		nodes.append(
			{
				"id": asset.name,
				"label": asset.asset_name or asset.name,
				"title": title,
				"group": group,
				"shape": "icon",
				"icon": {
					"face": "'Font Awesome 5 Free'",  # Important for correct FA5 rendering in Vis.js
					"weight": "900",  # Required for solid icons in FA5
					"code": icon,
					"size": 50,
					"color": "#28a745" if asset.status == "В експлуатації" else "#6c757d",
				},
			}
		)

	# Отримуємо всі з'єднання (порти, які мають connected_asset)
	ports = frappe.get_all(
		"oiNetworkPort",
		filters={"connected_asset": ["is", "set"]},
		fields=["asset", "connected_asset", "port_name", "last_speed"],
	)

	for port in ports:
		# Перевіряємо, чи обидва активи існують у нашій вибірці
		if port.asset in asset_map and port.connected_asset in asset_map:
			# Уникаємо дублювання зв'язків (A->B і B->A)
			edge_pair = tuple(sorted([port.asset, port.connected_asset]))
			if edge_pair not in added_edges:
				edges.append(
					{
						"from": port.asset,
						"to": port.connected_asset,
						"title": f"Port: {port.port_name}<br>Speed: {port.last_speed or 'Unknown'}",
						"color": {"color": "#848484", "highlight": "#007bff"},
					}
				)
				added_edges.add(edge_pair)

	return {"nodes": nodes, "edges": edges}
