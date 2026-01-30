# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Dashboard API для Orange Inventory.
Надає статистику та дані для dashboard.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime


@frappe.whitelist()
def get_dashboard_stats(asset_group: str | None = None):
	"""
	Повертає загальну статистику для dashboard.

	Args:
	        asset_group: Фільтр по групі активів (опціонально)
	"""
	stats = {}

	# Статистика агентів
	stats["agents"] = get_agent_stats(asset_group)

	# Статистика алертів
	stats["alerts"] = get_alert_stats(asset_group)

	# Статистика ресурсів
	stats["resources"] = get_resource_stats(asset_group)

	# Топ проблемних агентів
	stats["problem_agents"] = get_problem_agents(asset_group)

	# Список груп для фільтра
	stats["groups"] = get_asset_groups()

	return stats


def get_asset_groups():
	"""Повертає список груп активів для фільтра."""
	return frappe.get_all(
		"oiAssetGroup",
		filters={"is_active": 1},
		fields=["name", "group_name", "color", "agent_count"],
		order_by="group_name",
	)


def get_agent_stats(asset_group: str | None = None):
	"""Статистика агентів."""
	filters = {}
	if asset_group:
		filters["asset_group"] = asset_group

	total = frappe.db.count("oiAgent", filters)

	# Статуси з урахуванням групи
	group_condition = ""
	params = []
	if asset_group:
		group_condition = "WHERE asset_group = %s"
		params = [asset_group]

	status_counts = frappe.db.sql(
		f"""
		SELECT status, COUNT(*) as count
		FROM `taboiAgent`
		{group_condition}
		GROUP BY status
	""",
		params,
		as_dict=True,
	)

	status_map = {s["status"]: s["count"] for s in status_counts}

	# Агенти онлайн за останні 15 хвилин
	threshold = add_to_date(now_datetime(), minutes=-15)
	online_filters = {"last_seen": [">=", threshold]}
	if asset_group:
		online_filters["asset_group"] = asset_group
	online_count = frappe.db.count("oiAgent", online_filters)

	return {
		"total": total,
		"online": online_count,
		"offline": status_map.get("Офлайн", 0),
		"active": status_map.get("Активний", 0),
		"inactive": status_map.get("Неактивний", 0),
	}


def get_alert_stats(asset_group: str | None = None):
	"""Статистика алертів."""
	# Активні алерти з урахуванням групи
	if asset_group:
		active_alerts = frappe.db.sql(
			"""
			SELECT al.alert_type, al.severity, COUNT(*) as count
			FROM `taboiAgentAlert` al
			INNER JOIN `taboiAgent` a ON a.name = al.agent
			WHERE al.status = 'Активне' AND a.asset_group = %s
			GROUP BY al.alert_type, al.severity
		""",
			[asset_group],
			as_dict=True,
		)
	else:
		active_alerts = frappe.db.sql(
			"""
			SELECT alert_type, severity, COUNT(*) as count
			FROM `taboiAgentAlert`
			WHERE status = 'Активне'
			GROUP BY alert_type, severity
		""",
			as_dict=True,
		)

	# Підрахунок по severity
	severity_counts = {"Critical": 0, "Warning": 0, "Info": 0}
	type_counts = {}

	for alert in active_alerts:
		severity_counts[alert["severity"]] = severity_counts.get(alert["severity"], 0) + alert["count"]
		type_counts[alert["alert_type"]] = type_counts.get(alert["alert_type"], 0) + alert["count"]

	# Алерти за останні 24 години
	threshold_24h = add_to_date(now_datetime(), hours=-24)
	alerts_24h = frappe.db.count("oiAgentAlert", {"creation": [">=", threshold_24h]})

	# Вирішені за 24 години
	resolved_24h = frappe.db.count(
		"oiAgentAlert", {"status": "Вирішено", "resolved_at": [">=", threshold_24h]}
	)

	return {
		"active_total": sum(severity_counts.values()),
		"critical": severity_counts["Critical"],
		"warning": severity_counts["Warning"],
		"info": severity_counts["Info"],
		"by_type": type_counts,
		"new_24h": alerts_24h,
		"resolved_24h": resolved_24h,
	}


def get_resource_stats(asset_group: str | None = None):
	"""Середні показники використання ресурсів."""
	# Отримуємо останні snapshot для кожного агента
	group_condition = ""
	params = []
	if asset_group:
		group_condition = "AND a.asset_group = %s"
		params = [asset_group]

	latest_snapshots = frappe.db.sql(
		f"""
		SELECT s.cpu_usage, s.ram_usage, s.disk_usage
		FROM `taboiAgentSnapshot` s
		INNER JOIN (
			SELECT agent, MAX(timestamp) as max_ts
			FROM `taboiAgentSnapshot`
			GROUP BY agent
		) latest ON s.agent = latest.agent AND s.timestamp = latest.max_ts
		INNER JOIN `taboiAgent` a ON a.name = s.agent
		WHERE a.status = 'Активний' {group_condition}
	""",
		params,
		as_dict=True,
	)

	if not latest_snapshots:
		return {
			"avg_cpu": 0,
			"avg_ram": 0,
			"avg_disk": 0,
			"high_cpu_count": 0,
			"high_ram_count": 0,
			"high_disk_count": 0,
		}

	cpu_values = []
	ram_values = []
	disk_values = []
	high_cpu = 0
	high_ram = 0
	high_disk = 0

	for snapshot in latest_snapshots:
		if snapshot.cpu_usage:
			cpu_values.append(snapshot.cpu_usage)
			if snapshot.cpu_usage > 90:
				high_cpu += 1

		if snapshot.ram_usage:
			ram_values.append(snapshot.ram_usage)
			if snapshot.ram_usage > 90:
				high_ram += 1

		# Дискове використання з disk_usage (JSON)
		if snapshot.disk_usage:
			try:
				disks = (
					json.loads(snapshot.disk_usage)
					if isinstance(snapshot.disk_usage, str)
					else snapshot.disk_usage
				)
				if isinstance(disks, list):
					for disk in disks:
						usage = disk.get("used_percent") or disk.get("usage_percent", 0)
						disk_values.append(usage)
						if usage > 90:
							high_disk += 1
							break  # Рахуємо агента один раз
			except (json.JSONDecodeError, TypeError):
				pass

	return {
		"avg_cpu": round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0,
		"avg_ram": round(sum(ram_values) / len(ram_values), 1) if ram_values else 0,
		"avg_disk": round(sum(disk_values) / len(disk_values), 1) if disk_values else 0,
		"high_cpu_count": high_cpu,
		"high_ram_count": high_ram,
		"high_disk_count": high_disk,
	}


def get_problem_agents(asset_group: str | None = None):
	"""Список проблемних агентів (з активними алертами)."""
	group_condition = ""
	params = []
	if asset_group:
		group_condition = "AND a.asset_group = %s"
		params = [asset_group]

	problem_agents = frappe.db.sql(
		f"""
		SELECT
			a.name,
			a.hostname,
			a.status,
			a.last_seen,
			COUNT(al.name) as alert_count,
			MAX(CASE WHEN al.severity = 'Critical' THEN 1 ELSE 0 END) as has_critical
		FROM `taboiAgent` a
		INNER JOIN `taboiAgentAlert` al ON al.agent = a.name AND al.status = 'Активне'
		WHERE 1=1 {group_condition}
		GROUP BY a.name
		ORDER BY has_critical DESC, alert_count DESC
		LIMIT 10
	""",
		params,
		as_dict=True,
	)

	return problem_agents


@frappe.whitelist()
def get_agents_list():
	"""
	Повертає список агентів з їх поточним статусом.
	"""
	threshold = add_to_date(now_datetime(), minutes=-15)

	agents = frappe.db.sql(
		"""
		SELECT
			a.name,
			a.hostname,
			a.status,
			a.last_seen,
			a.agent_version,
			a.os,
			a.cpu_model,
			a.ram_total_gb,
			CASE WHEN a.last_seen >= %s THEN 1 ELSE 0 END as is_online,
			(SELECT COUNT(*) FROM `taboiAgentAlert` al
			 WHERE al.agent = a.name AND al.status = 'Активне') as active_alerts
		FROM `taboiAgent` a
		ORDER BY is_online DESC, a.hostname
	""",
		(threshold,),
		as_dict=True,
	)

	return agents


@frappe.whitelist()
def get_alert_timeline():
	"""
	Повертає timeline алертів за останні 7 днів.
	"""
	threshold = add_to_date(now_datetime(), days=-7)

	timeline = frappe.db.sql(
		"""
		SELECT
			DATE(creation) as date,
			alert_type,
			severity,
			COUNT(*) as count
		FROM `taboiAgentAlert`
		WHERE creation >= %s
		GROUP BY DATE(creation), alert_type, severity
		ORDER BY date DESC
	""",
		(threshold,),
		as_dict=True,
	)

	return timeline


@frappe.whitelist()
def get_version_distribution():
	"""
	Повертає розподіл версій агентів.
	"""
	versions = frappe.db.sql(
		"""
		SELECT
			agent_version as version,
			COUNT(*) as count
		FROM `taboiAgent`
		WHERE agent_version IS NOT NULL AND agent_version != ''
		GROUP BY agent_version
		ORDER BY count DESC
	""",
		as_dict=True,
	)

	return versions


@frappe.whitelist()
def get_agent_history(agent: str, hours: int = 24):
	"""
	Повертає історію snapshots для агента для побудови графіків.

	Args:
	        agent: ID агента
	        hours: кількість годин історії (за замовчуванням 24)

	Returns:
	        dict: {
	                "labels": ["10:00", "11:00", ...],
	                "cpu": [45.2, 50.1, ...],
	                "ram": [60.5, 62.3, ...],
	                "disk": [75.0, 75.1, ...]
	        }
	"""
	from frappe.utils import cint

	hours = cint(hours) or 24
	threshold = add_to_date(now_datetime(), hours=-hours)

	snapshots = frappe.db.sql(
		"""
		SELECT
			timestamp,
			cpu_usage,
			ram_usage,
			disk_usage
		FROM `taboiAgentSnapshot`
		WHERE agent = %s AND timestamp >= %s
		ORDER BY timestamp ASC
	""",
		(agent, threshold),
		as_dict=True,
	)

	if not snapshots:
		return {"labels": [], "cpu": [], "ram": [], "disk": []}

	labels = []
	cpu_data = []
	ram_data = []
	disk_data = []

	for snap in snapshots:
		# Форматуємо мітку часу
		if snap.timestamp:
			labels.append(snap.timestamp.strftime("%H:%M"))

		cpu_data.append(round(snap.cpu_usage or 0, 1))
		ram_data.append(round(snap.ram_usage or 0, 1))

		# Отримуємо максимальне використання диску
		disk_max = 0
		if snap.disk_usage:
			try:
				disks = json.loads(snap.disk_usage) if isinstance(snap.disk_usage, str) else snap.disk_usage
				if isinstance(disks, list) and disks:
					disk_max = max(d.get("used_percent", 0) for d in disks)
			except (json.JSONDecodeError, TypeError):
				pass
		disk_data.append(round(disk_max, 1))

	return {"labels": labels, "cpu": cpu_data, "ram": ram_data, "disk": disk_data, "count": len(snapshots)}


@frappe.whitelist()
def get_agent_current_metrics(agent: str):
	"""
	Повертає поточні метрики агента з останнього snapshot.

	Args:
	        agent: ID агента

	Returns:
	        dict: поточні показники CPU, RAM, Disk
	"""
	snapshot = frappe.db.sql(
		"""
		SELECT
			timestamp,
			cpu_usage,
			ram_usage,
			disk_usage,
			current_user,
			uptime_seconds,
			ip_addresses
		FROM `taboiAgentSnapshot`
		WHERE agent = %s
		ORDER BY timestamp DESC
		LIMIT 1
	""",
		(agent,),
		as_dict=True,
	)

	if not snapshot:
		return None

	snap = snapshot[0]

	# Парсимо disk_usage
	disk_info = []
	if snap.disk_usage:
		try:
			disk_info = json.loads(snap.disk_usage) if isinstance(snap.disk_usage, str) else snap.disk_usage
		except (json.JSONDecodeError, TypeError):
			pass

	# Парсимо ip_addresses
	ip_addresses = []
	if snap.ip_addresses:
		try:
			ip_addresses = (
				json.loads(snap.ip_addresses) if isinstance(snap.ip_addresses, str) else snap.ip_addresses
			)
		except (json.JSONDecodeError, TypeError):
			pass

	return {
		"timestamp": snap.timestamp,
		"cpu_usage": round(snap.cpu_usage or 0, 1),
		"ram_usage": round(snap.ram_usage or 0, 1),
		"disks": disk_info,
		"current_user": snap.current_user,
		"uptime_seconds": snap.uptime_seconds,
		"ip_addresses": ip_addresses,
	}
