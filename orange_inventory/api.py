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


# ===== Migration Helper Functions =====


@frappe.whitelist()
def auto_populate_employee_mapping():
	"""Автозаповнення oiEmployeeMapping на основі full_name"""
	old_employees = frappe.get_all("oiEmployee", fields=["name", "full_name"])
	created = 0
	skipped = 0

	for old_emp in old_employees:
		# Перевірка чи вже існує mapping
		if frappe.db.exists("oiEmployeeMapping", {"old_employee": old_emp.name}):
			skipped += 1
			continue

		# Пошук hromsEmployee за full_name
		new_emp = frappe.db.get_value("hromsEmployee", {"full_name": old_emp.full_name}, "name")

		if new_emp:
			frappe.get_doc(
				{"doctype": "oiEmployeeMapping", "old_employee": old_emp.name, "new_employee": new_emp}
			).insert(ignore_permissions=True)
			created += 1

	frappe.db.commit()
	return {"status": "success", "created": created, "skipped": skipped, "total": len(old_employees)}


@frappe.whitelist()
def auto_populate_organization_mapping():
	"""Автозаповнення oiOrganizationMapping на основі organization_name"""
	old_orgs = frappe.get_all("oiOrganization", fields=["name", "organization_name"])
	created = 0
	skipped = 0

	for old_org in old_orgs:
		# Перевірка чи вже існує mapping
		if frappe.db.exists("oiOrganizationMapping", {"old_organization": old_org.name}):
			skipped += 1
			continue

		# Пошук hromsOrgStructure за department_name
		new_org = frappe.db.get_value(
			"hromsOrgStructure", {"department_name": old_org.organization_name}, "name"
		)

		if new_org:
			frappe.get_doc(
				{
					"doctype": "oiOrganizationMapping",
					"old_organization": old_org.name,
					"new_organization": new_org,
				}
			).insert(ignore_permissions=True)
			created += 1

	frappe.db.commit()
	return {"status": "success", "created": created, "skipped": skipped, "total": len(old_orgs)}


@frappe.whitelist()
def migrate_employee_references():
	"""Оновлення всіх Link-полів з oiEmployee на hromsEmployee"""
	from frappe.utils import now

	mappings = frappe.get_all(
		"oiEmployeeMapping", filters={"migrated": 0}, fields=["name", "old_employee", "new_employee"]
	)

	if not mappings:
		return {"status": "warning", "message": "No unmigrated employee mappings found"}

	# Таблиці для оновлення (DocType: [fieldnames])
	tables_to_update = {
		"oiAsset": ["responsible_employee", "asset_user"],
		"oiIssueOrder": ["to_employee"],
		"oiServiceRequest": ["requester", "assigned_to"],
		"oiLocation": ["responsible_user"],
		"oiContract": ["responsible_person"],
		"oiCourseSubmission": ["employee"],
		"oiCorrespondence": ["executor"],
		"oiPriceMonitoring": ["responsible_person", "approved_by"],
	}

	migrated_count = 0
	for mapping in mappings:
		old_name = mapping.old_employee
		new_name = mapping.new_employee

		for doctype, fields in tables_to_update.items():
			for field in fields:
				try:
					frappe.db.sql(
						f"""
						UPDATE `tab{doctype}`
						SET `{field}` = %s
						WHERE `{field}` = %s
					""",
						(new_name, old_name),
					)
				except Exception as e:
					frappe.log_error(f"Error migrating {doctype}.{field}: {e}")

		# Позначити як мігрований
		frappe.db.set_value("oiEmployeeMapping", mapping.name, {"migrated": 1, "migration_date": now()})
		migrated_count += 1

	frappe.db.commit()
	return {"status": "success", "migrated": migrated_count}


@frappe.whitelist()
def migrate_organization_references():
	"""Оновлення всіх Link-полів з oiOrganization на hromsOrgStructure"""
	from frappe.utils import now

	mappings = frappe.get_all(
		"oiOrganizationMapping",
		filters={"migrated": 0},
		fields=["name", "old_organization", "new_organization"],
	)

	if not mappings:
		return {"status": "warning", "message": "No unmigrated organization mappings found"}

	# Таблиці для оновлення
	tables_to_update = {
		"oiAsset": ["current_owner"],
		"oiIssueOrder": ["from_organization", "to_organization"],
		"oiReceiptOrder": ["to_organization"],
		"oiHromadaSurvey": ["master_info"],
		"oiPeriodicReport": ["organization"],
		"oiServiceRequest": ["requester_organization"],
		"oiCorrespondence": ["correspondent", "addressee"],
		"oiEmployee": ["organization", "department"],
	}

	# Dynamic Links (oiAssetMovementHistory)
	dynamic_link_fields = [
		("oiAssetMovementHistory", "from_source_name", "from_source_type"),
		("oiAssetMovementHistory", "to_source_name", "to_source_type"),
	]

	migrated_count = 0
	for mapping in mappings:
		old_name = mapping.old_organization
		new_name = mapping.new_organization

		# Звичайні Link поля
		for doctype, fields in tables_to_update.items():
			for field in fields:
				try:
					frappe.db.sql(
						f"""
						UPDATE `tab{doctype}`
						SET `{field}` = %s
						WHERE `{field}` = %s
					""",
						(new_name, old_name),
					)
				except Exception as e:
					frappe.log_error(f"Error migrating {doctype}.{field}: {e}")

		# Dynamic Links - оновлюємо і значення, і тип
		for doctype, value_field, type_field in dynamic_link_fields:
			try:
				frappe.db.sql(
					f"""
					UPDATE `tab{doctype}`
					SET `{value_field}` = %s, `{type_field}` = 'hromsOrgStructure'
					WHERE `{value_field}` = %s
					AND `{type_field}` = 'oiOrganization'
				""",
					(new_name, old_name),
				)
			except Exception as e:
				frappe.log_error(f"Error migrating dynamic link {doctype}.{value_field}: {e}")

		# Позначити як мігрований
		frappe.db.set_value("oiOrganizationMapping", mapping.name, {"migrated": 1, "migration_date": now()})
		migrated_count += 1

	frappe.db.commit()
	return {"status": "success", "migrated": migrated_count}


@frappe.whitelist()
def get_migration_status():
	"""Отримати статус міграції"""
	emp_total = frappe.db.count("oiEmployee")
	emp_mapped = frappe.db.count("oiEmployeeMapping")
	emp_migrated = frappe.db.count("oiEmployeeMapping", {"migrated": 1})

	org_total = frappe.db.count("oiOrganization")
	org_mapped = frappe.db.count("oiOrganizationMapping")
	org_migrated = frappe.db.count("oiOrganizationMapping", {"migrated": 1})

	return {
		"employee": {
			"total": emp_total,
			"mapped": emp_mapped,
			"migrated": emp_migrated,
			"unmapped": emp_total - emp_mapped,
		},
		"organization": {
			"total": org_total,
			"mapped": org_mapped,
			"migrated": org_migrated,
			"unmapped": org_total - org_mapped,
		},
	}
