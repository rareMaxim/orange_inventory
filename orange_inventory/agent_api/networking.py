# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import hashlib
import json

import frappe

from orange_inventory.agent_api.software import _is_rule_applicable
from orange_inventory.agent_api.utils import _log
from orange_inventory.discovery_utils import get_manufacturer_from_mac


def _normalize_port_name(name: str) -> str:
	"""Нормалізує назву порту для кращого зіставлення (напр. Eth1 -> ether1)."""
	if not name:
		return ""
	n = name.lower().strip()
	if "ether" not in n:
		n = n.replace("eth ", "ether").replace("eth", "ether")
	return n


def _sync_network_ports(asset_name: str, adapters: list):
	"""Синхронізує мережеві адаптери від агента з портами oiNetworkPort."""
	for adapter in adapters:
		mac = adapter.get("mac_address", "").lower().strip()
		name = adapter.get("name", "Unknown")

		if not mac or mac == "00:00:00:00:00:00":
			continue

		normalized_name = _normalize_port_name(name)

		# Збираємо всі порти, які нормалізуються до цього імені
		all_matching_ports = []
		all_ports = frappe.get_all(
			"oiNetworkPort", filters={"asset": asset_name}, fields=["name", "port_name", "mac_address"]
		)
		for p in all_ports:
			if _normalize_port_name(p.port_name) == normalized_name:
				all_matching_ports.append(p)

		existing_port = None
		if all_matching_ports:
			# Пріоритет: порт, який починається з Eth, або порт зі збігом MAC
			all_matching_ports.sort(
				key=lambda x: (
					1 if x.port_name.startswith("Eth") else 0,
					1 if x.mac_address == mac else 0,
					-len(x.port_name),  # Довший зазвичай краще (Eth1 vs ether1)
				),
				reverse=True,
			)

			existing_port = all_matching_ports[0].name

			# Видаляємо інші дублікати
			for p in all_matching_ports[1:]:
				frappe.db.delete("oiNetworkPort", p.name)
				_log(
					f"Discovery: Merging/Deleting duplicate port {p.port_name} into {all_matching_ports[0].port_name}"
				)

		if not existing_port:
			port = frappe.get_doc(
				{
					"doctype": "oiNetworkPort",
					"asset": asset_name,
					"port_name": name,
					"port_type": "Ethernet",
					"mac_address": mac,
				}
			)
			port.insert(ignore_permissions=True)
		else:
			frappe.db.set_value("oiNetworkPort", existing_port, "mac_address", mac)


def _process_neighbors(agent_name: str, asset_name: str, neighbors: list):
	"""Обробляє список мережевих сусідів та створює зв'язки oiNetworkPort."""
	if not asset_name or not neighbors:
		return

	try:
		_log(f"Discovery: processing {len(neighbors)} neighbors for agent {agent_name}")
		for neighbor in neighbors:
			neighbor_mac = neighbor.get("mac_address", "").lower().strip()
			neighbor_ip = neighbor.get("ip_address")
			if not neighbor_mac or neighbor_mac == "00:00:00:00:00:00":
				continue

			_log(f"Discovery: investigating neighbor {neighbor_mac} ({neighbor_ip})")
			neighbor_asset = frappe.db.get_value("oiNetworkPort", {"mac_address": neighbor_mac}, "asset")
			if not neighbor_asset:
				neighbor_asset = frappe.db.sql(
					"""
					SELECT name FROM `taboiAsset`
					WHERE mac_addresses LIKE %s
				""",
					(f"%{neighbor_mac}%",),
					as_dict=True,
				)
				if neighbor_asset:
					neighbor_asset = neighbor_asset[0].name

			if not neighbor_asset:
				if neighbor.get("interface") == "SNMP-Discovery":
					# Не створюємо активи для випадкових MAC-адрес із таблиці bridge FDB
					continue

				_log(f"Discovery: Found new device {neighbor_mac} ({neighbor_ip}), creating Asset...")
				manufacturer = get_manufacturer_from_mac(neighbor_mac)
				asset = frappe.new_doc("oiAsset")
				asset.asset_name = f"Discovered-{neighbor_mac[-8:]}"
				asset.ip_address = neighbor_ip
				asset.mac_addresses = neighbor_mac
				asset.is_network_device = 1
				asset.manufacturer = manufacturer
				asset.status = "В експлуатації"
				asset.insert(ignore_permissions=True)
				neighbor_asset = asset.name

				port = frappe.new_doc("oiNetworkPort")
				port.asset = neighbor_asset
				port.port_name = "Auto-MGMT"
				port.mac_address = neighbor_mac
				port.insert(ignore_permissions=True)

			if neighbor_asset and neighbor_asset != asset_name:
				iface = neighbor.get("interface") or "eth0"

				# Пріоритет: якщо це бездротовий порт, а у нас є спільні MAC з інфраструктурою (CAPsMAN),
				# то краще ігнорувати цей зв'язок, якщо він суперечить дротовому.
				is_wireless = any(x in iface.lower() for x in ["wlan", "wifi", "cap"])

				normalized_iface = _normalize_port_name(iface)
				my_port_name = iface  # Дефолт

				# Шукаємо існуючий порт за нормалізованим іменем
				all_asset_ports = frappe.get_all(
					"oiNetworkPort", filters={"asset": asset_name}, fields=["name", "port_name"]
				)
				my_port_id = None
				for p in all_asset_ports:
					if _normalize_port_name(p.port_name) == normalized_iface:
						my_port_id = p.name
						my_port_name = p.port_name
						break

				if not my_port_id:
					# Якщо порт не знайдено, створюємо "Auto-" порт, але тільки якщо це не SNMP-Discovery
					if iface == "SNMP-Discovery":
						continue

					my_port_name = f"Auto-{iface}"
					my_port = frappe.get_doc(
						{
							"doctype": "oiNetworkPort",
							"asset": asset_name,
							"port_name": my_port_name,
							"port_type": "Ethernet",
						}
					)
					my_port.insert(ignore_permissions=True)
					my_port_id = my_port.name
				else:
					my_port = frappe.get_doc("oiNetworkPort", my_port_id)

				# ПЕРЕВІРКА ПРІОРИТЕТУ: Не підключаємо той самий актив до бездротового порту,
				# якщо він вже підключений до якогось дротового порту цього ж пристрою.
				if is_wireless:
					already_connected_wired = frappe.db.sql(
						"""
						SELECT name FROM `taboiNetworkPort`
						WHERE asset = %s
						AND connected_asset = %s
						AND port_name NOT LIKE '%%wlan%%'
						AND port_name NOT LIKE '%%wifi%%'
						AND port_name NOT LIKE '%%cap%%'
					""",
						(asset_name, neighbor_asset),
					)
					if already_connected_wired:
						_log(
							f"Discovery: Skipping wireless connection for {neighbor_asset} on {asset_name} because wired connection already exists."
						)
						continue

				their_port_name = frappe.db.get_value("oiNetworkPort", {"mac_address": neighbor_mac}, "name")
				if not their_port_name:
					their_port_name = "Auto-Discovery"
					if not frappe.db.exists(
						"oiNetworkPort", {"asset": neighbor_asset, "port_name": their_port_name}
					):
						their_port = frappe.get_doc(
							{
								"doctype": "oiNetworkPort",
								"asset": neighbor_asset,
								"port_name": their_port_name,
								"port_type": "Ethernet",
								"mac_address": neighbor_mac,
							}
						)
						their_port.insert(ignore_permissions=True)
						their_port_name = their_port.name
					else:
						their_port_name = frappe.db.get_value(
							"oiNetworkPort", {"asset": neighbor_asset, "port_name": their_port_name}, "name"
						)

				if my_port.connection != their_port_name:
					my_port.connection = their_port_name
					my_port.connected_asset = neighbor_asset
					my_port.save(ignore_permissions=True)

	except Exception as e:
		frappe.log_error(f"Помилка при обробці мережевих сусідів: {str(e)}", "Agent API Discovery")


@frappe.whitelist()
def get_blocked_domains(agent_id=None):
	"""Повертає список заблокованих доменів для enforcement на агентах."""
	domains_list = []
	agent_name = None
	agent_group = None
	if agent_id:
		agent_data = frappe.get_value("oiAgent", {"agent_id": agent_id}, ["name", "asset_group"])
		if agent_data:
			agent_name, agent_group = agent_data

	blocked = frappe.get_all(
		"oiBlockedDomain",
		filters={"enabled": 1},
		fields=["name", "domain", "block_method", "redirect_ip", "include_subdomains", "reason"],
	)

	for item in blocked:
		if agent_id and agent_name:
			if not _is_rule_applicable(item.name, "oiBlockedDomain", agent_name, agent_group):
				continue
		domains_list.append(
			{
				"domain": item.domain,
				"method": item.block_method,
				"redirect_ip": item.redirect_ip or "0.0.0.0",
				"include_subdomains": bool(item.include_subdomains),
				"reason": item.reason or "Заборонено політикою",
			}
		)

	version_input = json.dumps(domains_list, sort_keys=True) + (agent_id or "")
	version_hash = hashlib.md5(version_input.encode()).hexdigest()[:8]
	return {"domains": domains_list, "version": version_hash, "count": len(domains_list)}
