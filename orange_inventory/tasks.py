# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Scheduled tasks для Orange Inventory.
"""

import frappe
from frappe.utils import add_to_date, now_datetime


def mark_offline_agents():
	"""
	Позначає агентів як 'Офлайн' якщо вони не відповідали більше 30 хвилин.

	Запускається кожні 15 хвилин через scheduler.
	"""
	# Поріг - 30 хвилин без зв'язку
	threshold = add_to_date(now_datetime(), minutes=-30)

	# Знаходимо агентів які не відповідали і ще не офлайн
	frappe.db.sql(
		"""
		UPDATE `taboiAgent`
		SET status = 'Офлайн'
		WHERE last_seen < %s
		AND status IN ('Активний', 'Неактивний')
		""",
		threshold,
	)

	frappe.db.commit()


def cleanup_old_snapshots():
	"""
	Видаляє старі snapshots (старші 30 днів) для економії місця.

	Запускається щодня.
	"""
	# Поріг - 30 днів
	threshold = add_to_date(now_datetime(), days=-30)

	# Видаляємо старі записи
	frappe.db.sql(
		"""
		DELETE FROM `taboiAgentSnapshot`
		WHERE timestamp < %s
		""",
		threshold,
	)

	frappe.db.commit()


def all():
	"""Запускається щохвилини."""
	pass


def hourly():
	"""Запускається щогодини."""
	mark_offline_agents()


def daily():
	"""Запускається щодня."""
	cleanup_old_snapshots()
