# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe

from orange_inventory.agent_api.networking import _process_neighbors
from orange_inventory.agent_api.utils import _log


@frappe.whitelist()
def get_snmp_targets(agent_id: str):
	"""Повертає список цілей для SNMP-сканування, закріплених за цим агентом."""
	if not agent_id:
		return []
	agent_name = frappe.db.get_value("oiAgent", {"agent_id": agent_id}, "name")
	if not agent_name:
		return []
	assets = frappe.get_all(
		"oiAsset",
		filters={"scanning_agent": agent_name, "ip_address": ["is", "set"]},
		fields=["name", "ip_address", "snmp_community"],
	)
	targets = []
	for asset in assets:
		targets.append(
			{
				"asset_name": asset.name,
				"ip": asset.ip_address,
				"community": asset.snmp_community or "public",
				"version": "2c",
			}
		)
	return targets


def _process_snmp_reports(agent_name: str, reports: list):
	"""Обробляє SNMP звіти, отримані від агента."""
	for report in reports:
		asset_name = report.get("asset_name")
		if not asset_name or not frappe.db.exists("oiAsset", asset_name):
			_log(f"SNMP: Asset {asset_name} not found, skipping report from {agent_name}")
			continue

		error = report.get("error")
		if error:
			_log(f"SNMP: Agent {agent_name} reported error for {asset_name} ({report.get('ip')}): {error}")

		interfaces = report.get("interfaces") or []
		_log(f"SNMP: Processing {len(interfaces)} interfaces for {asset_name} from {agent_name}")

		all_macs = []
		for iface in interfaces:
			ifname = iface.get("name")
			mac = iface.get("mac", "").lower().strip()
			status = iface.get("status")
			speed = iface.get("speed")
			idx = iface.get("index")

			if mac and mac != "00:00:00:00:00:00":
				all_macs.append(mac)

			port_name = frappe.db.get_value(
				"oiNetworkPort", {"asset": asset_name, "port_name": ifname}, "name"
			)
			if not port_name and idx:
				port_name = frappe.db.get_value(
					"oiNetworkPort", {"asset": asset_name, "snmp_index": idx}, "name"
				)

			if not port_name:
				port = frappe.new_doc("oiNetworkPort")
				port.asset = asset_name
				port.port_name = ifname
				port.snmp_index = idx
				port.mac_address = mac
				port.insert(ignore_permissions=True)
				port_name = port.name

			frappe.db.set_value(
				"oiNetworkPort",
				port_name,
				{
					"mac_address": mac,
					"is_active": 1 if status == 1 else 0,
					"last_speed": _format_speed(speed) if speed else None,
					"snmp_index": idx,
				},
				update_modified=False,
			)

		# 6. Обробляємо сусідів (якщо вони є)
		neighbors = report.get("neighbors")
		if neighbors:
			_log(f"SNMP: Processing {len(neighbors)} neighbors for {asset_name} from {agent_name}")
			_process_neighbors(agent_name, asset_name, neighbors)

		if all_macs:
			current_macs = frappe.db.get_value("oiAsset", asset_name, "mac_addresses") or ""
			new_macs_str = ", ".join(sorted(list(set(all_macs))))
			if current_macs != new_macs_str:
				frappe.db.set_value("oiAsset", asset_name, "mac_addresses", new_macs_str)


def _format_speed(speed_bps: int) -> str:
	"""Форматує швидкість у людиночитаний вигляд."""
	if not speed_bps:
		return "0 bps"
	if speed_bps >= 1_000_000_000:
		return f"{speed_bps / 1_000_000_000:.1f} Gbps"
	if speed_bps >= 1_000_000:
		return f"{speed_bps / 1_000_000:.1f} Mbps"
	if speed_bps >= 1_000:
		return f"{speed_bps / 1_000:.1f} Kbps"
	return f"{speed_bps} bps"
