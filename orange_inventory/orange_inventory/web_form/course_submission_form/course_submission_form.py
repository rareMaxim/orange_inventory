import frappe
from frappe.utils import today


def get_context(context):
	"""Встановлюємо дефолтні значення для форми"""
	# Встановлюємо поточну дату для completion_date
	if context.doc and not context.doc.get("completion_date"):
		context.doc.completion_date = today()
