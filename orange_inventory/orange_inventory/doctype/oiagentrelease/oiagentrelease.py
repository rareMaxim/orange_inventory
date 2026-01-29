# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import hashlib
import os

import frappe
from frappe.model.document import Document


class oiAgentRelease(Document):
	def validate(self):
		self.calculate_checksum()

	def on_update(self):
		# Якщо ця версія позначена як актуальна - зняти позначку з інших
		if self.is_latest:
			frappe.db.sql(
				"""
				UPDATE `taboiAgentRelease`
				SET is_latest = 0
				WHERE name != %s AND is_latest = 1
			""",
				(self.name,),
			)

	def calculate_checksum(self):
		"""Обчислює SHA256 checksum для прикріпленого файлу."""
		if not self.agent_file:
			return

		# Отримуємо шлях до файлу
		file_doc = frappe.get_doc("File", {"file_url": self.agent_file})
		if not file_doc:
			return

		file_path = file_doc.get_full_path()
		if not os.path.exists(file_path):
			return

		# Обчислюємо checksum
		sha256_hash = hashlib.sha256()
		with open(file_path, "rb") as f:
			for chunk in iter(lambda: f.read(4096), b""):
				sha256_hash.update(chunk)

		self.file_checksum = sha256_hash.hexdigest()
		self.file_size = os.path.getsize(file_path)
