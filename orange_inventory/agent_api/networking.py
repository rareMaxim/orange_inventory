# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import hashlib
import json

import frappe

from orange_inventory.agent_api.software import _is_rule_applicable
from orange_inventory.agent_api.utils import _log
from orange_inventory.discovery_utils import get_manufacturer_from_mac


def _sync_network_ports(asset_name: str, adapters: list):
	"""Синхронізує мережеві адаптери від агента з портами oiNetworkPort."""
	for adapter in adapters:
		mac = adapter.get("mac_address", "").lower().strip()
		name = adapter.get("name", "Unknown")

		if not mac or mac == "00:00:00:00:00:00":
			continue

		existing_port = frappe.db.get_value(
			"oiNetworkPort", {"asset": asset_name, "mac_address": mac}, "name"
		)

		if not existing_port:
			full_port_id = f"Auto-{name}"
			existing_port = frappe.db.get_value(
				"oiNetworkPort", {"asset": asset_name, "port_name": full_port_id}, "name"
			)
			if not existing_port:
				existing_port = frappe.db.get_value(
					"oiNetworkPort", {"asset": asset_name, "port_name": name}, "name"
				)

		if not existing_port:
			port = frappe.get_doc(
				{
					"doctype": "oiNetworkPort",
					"asset": asset_name,
					"port_name": f"Auto-{name}",
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
				my_port_name = f"Auto-{iface}-{neighbor_mac[-8:]}"
				if not frappe.db.exists("oiNetworkPort", {"asset": asset_name, "port_name": my_port_name}):
					my_port = frappe.get_doc(
						{
							"doctype": "oiNetworkPort",
							"asset": asset_name,
							"port_name": my_port_name,
							"port_type": "Ethernet",
						}
					)
					my_port.insert(ignore_permissions=True)
				else:
					my_port = frappe.get_doc(
						"oiNetworkPort", {"asset": asset_name, "port_name": my_port_name}
					)

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
