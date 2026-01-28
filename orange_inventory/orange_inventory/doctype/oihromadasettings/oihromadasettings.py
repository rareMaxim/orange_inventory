# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHromadaSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_base_url: DF.Data
		api_token: DF.Password
		community_id: DF.Int
		last_sync_date: DF.Datetime | None
		mapped_parameters: DF.Int
		sync_log: DF.Code | None
		total_parameters: DF.Int
		unmapped_parameters: DF.Int
	# end: auto-generated types

	def validate(self):
		if not self.api_base_url:
			self.api_base_url = "https://backend.hromada.gov.ua/api"


def get_settings():
	"""Отримати налаштування інтеграції з hromada.gov.ua."""
	return frappe.get_single("oiHromadaSettings")


def get_api_headers():
	"""Отримати заголовки для API запитів."""
	settings = get_settings()
	token = settings.get_password("api_token")
	if not token:
		frappe.throw("API Token не налаштовано. Перейдіть до oiHromadaSettings.")
	return {
		"accept": "application/json, text/plain, */*",
		"authorization": f"Bearer {token}",
		"content-type": "application/json",
		"origin": "https://hromada.gov.ua",
		"referer": "https://hromada.gov.ua/",
	}
