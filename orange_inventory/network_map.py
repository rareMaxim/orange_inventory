import frappe


@frappe.whitelist()
def get_network_graph_data():
	"""
	Збирає дані про всі мережеві пристрої та з'єднання між ними
	для побудови візуальної карти мережі.
	"""
	# 1. Отримуємо всі мережеві пристрої (це будуть "вузли" нашого графа)
	nodes = frappe.get_all(
		"oiAsset", fields=["name as id", "asset_name as label"], filters={"is_network_device": 1}
	)

	# 2. Отримуємо всі порти, які мають з'єднання
	connections = frappe.get_all(
		"oiNetworkPort",
		fields=["name", "asset", "connection", "connected_asset"],
		filters={"connection": ("is", "set")},
	)

	# 3. Формуємо "лінії" (зв'язки) для графа
	edges = []
	processed_connections = set()  # Допоможе уникнути дублювання зв'язків

	for conn in connections:
		# Створюємо унікальний ключ для пари з'єднань, щоб не дублювати їх
		# (наприклад, зв'язок А->Б такий самий, як Б->А)
		pair_key = tuple(sorted((conn.asset, conn.connected_asset)))

		if pair_key not in processed_connections:
			edges.append(
				{"from": conn.asset, "to": conn.connected_asset, "label": f"{conn.name} ↔ {conn.connection}"}
			)
			processed_connections.add(pair_key)

	return {"nodes": nodes, "edges": edges}
