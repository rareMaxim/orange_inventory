import frappe
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password


def _assert_view_permission(credential: str):
	# Базова перевірка DocPerm + додаткові обмеження при потребі
	if not frappe.has_permission("oiCredential", "read", credential):
		frappe.throw("Немає доступу до цього Credential", frappe.PermissionError)


@frappe.whitelist()
def reveal_secret(credential: str, reason: str | None = None):
	"""Повертає розшифрований секрет із oiCredential.secret та логує доступ"""
	_assert_view_permission(credential)

	secret = get_decrypted_password("oiCredential", credential, "secret", raise_exception=False)

	# Лог доступу (не розкриваємо секрет у логах)
	try:
		frappe.get_doc(
			{
				"doctype": "oiCredentialAccessLog",
				"credential": credential,
				"user": frappe.session.user,
				"timestamp": now_datetime(),
				"ip_address": getattr(frappe.local, "request_ip", None),
				"user_agent": getattr(frappe.local, "request_user_agent", None),
				"reason": reason,
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error("Не вдалося записати oiCredentialAccessLog", "oiCredential reveal_secret")

	return secret or ""
