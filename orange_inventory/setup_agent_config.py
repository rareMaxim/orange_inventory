import json

import frappe
from frappe.core.doctype.user.user import generate_keys


def setup():
	import random
	import string

	def get_random(length=15):
		return "".join(random.choices(string.ascii_letters + string.digits, k=length))

	user = frappe.get_doc("User", "Administrator")
	key = get_random()
	sec = get_random()
	user.api_key = key
	user.api_secret = sec
	user.save(ignore_permissions=True)
	frappe.db.commit()

	config = {"server_url": "http://127.0.0.1:8000", "api_key": key, "api_secret": sec}

	import os

	config_path = os.path.join(frappe.get_app_path("orange_inventory"), "..", "agent", "config.json")
	with open(config_path, "w") as f:
		json.dump(config, f)

	print("Agent config created.")


if __name__ == "__main__":
	setup()

if __name__ == "__main__":
	setup()
