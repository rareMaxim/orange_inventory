# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class oiMigrationSettings(Document):
	def onload(self):
		"""Завантажує статус при відкритті форми."""
		self.refresh_status()

	@frappe.whitelist()
	def refresh_status(self):
		"""Оновлює статистику mapping та міграції."""
		# Employee stats
		total_old_emp = frappe.db.count("oiEmployee")
		mapped_emp = frappe.db.count("oiEmployeeMapping")

		self.total_old_employees = total_old_emp
		self.mapped_employees = mapped_emp
		self.unmapped_employees = total_old_emp - mapped_emp

		# Organization stats
		total_old_org = frappe.db.count("oiOrganization")
		mapped_org = frappe.db.count("oiOrganizationMapping")

		self.total_old_organizations = total_old_org
		self.mapped_organizations = mapped_org
		self.unmapped_organizations = total_old_org - mapped_org

		# HTML статус
		self.migration_status_html = self._build_status_html()

	def _build_status_html(self):
		"""Створює HTML з візуальним статусом."""
		emp_pct = (self.mapped_employees / self.total_old_employees * 100) if self.total_old_employees else 0
		org_pct = (
			(self.mapped_organizations / self.total_old_organizations * 100)
			if self.total_old_organizations
			else 0
		)

		emp_color = "success" if emp_pct == 100 else ("warning" if emp_pct > 0 else "danger")
		org_color = "success" if org_pct == 100 else ("warning" if org_pct > 0 else "danger")

		return f"""
		<div class="row">
			<div class="col-md-6">
				<div class="progress" style="height: 25px; margin-bottom: 10px;">
					<div class="progress-bar bg-{emp_color}" style="width: {emp_pct}%;">
						Employee: {emp_pct:.0f}%
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="progress" style="height: 25px; margin-bottom: 10px;">
					<div class="progress-bar bg-{org_color}" style="width: {org_pct}%;">
						Organization: {org_pct:.0f}%
					</div>
				</div>
			</div>
		</div>
		"""

	def _add_log(self, message):
		"""Додає запис в лог."""
		timestamp = now()
		log_entry = f"[{timestamp}] {message}\n"
		self.migration_log = (self.migration_log or "") + log_entry

	@frappe.whitelist()
	def auto_populate_employee_mapping(self):
		"""Автозаповнення Employee Mapping."""
		from orange_inventory.api import auto_populate_employee_mapping

		self._add_log("Початок автозаповнення Employee Mapping...")
		result = auto_populate_employee_mapping()
		self._add_log(f"Результат: створено {result.get('created', 0)}, пропущено {result.get('skipped', 0)}")

		if result.get("errors"):
			for err in result["errors"][:10]:  # Перші 10 помилок
				self._add_log(f"  Помилка: {err}")

		self.refresh_status()
		self.save()
		return result

	@frappe.whitelist()
	def auto_populate_organization_mapping(self):
		"""Автозаповнення Organization Mapping."""
		from orange_inventory.api import auto_populate_organization_mapping

		self._add_log("Початок автозаповнення Organization Mapping...")
		result = auto_populate_organization_mapping()
		self._add_log(f"Результат: створено {result.get('created', 0)}, пропущено {result.get('skipped', 0)}")

		if result.get("errors"):
			for err in result["errors"][:10]:
				self._add_log(f"  Помилка: {err}")

		self.refresh_status()
		self.save()
		return result

	@frappe.whitelist()
	def migrate_employee_references(self):
		"""Міграція Employee посилань."""
		from orange_inventory.api import migrate_employee_references

		self._add_log("Початок міграції Employee посилань...")
		result = migrate_employee_references()
		self._add_log(f"Результат: оновлено {result.get('updated', 0)} записів")

		if result.get("details"):
			for dt, count in result["details"].items():
				self._add_log(f"  {dt}: {count}")

		self.refresh_status()
		self.save()
		return result

	@frappe.whitelist()
	def migrate_organization_references(self):
		"""Міграція Organization посилань."""
		from orange_inventory.api import migrate_organization_references

		self._add_log("Початок міграції Organization посилань...")
		result = migrate_organization_references()
		self._add_log(f"Результат: оновлено {result.get('updated', 0)} записів")

		if result.get("details"):
			for dt, count in result["details"].items():
				self._add_log(f"  {dt}: {count}")

		self.refresh_status()
		self.save()
		return result

	@frappe.whitelist()
	def clear_log(self):
		"""Очищає лог."""
		self.migration_log = ""
		self.save()

	@frappe.whitelist()
	def get_unmapped_employees(self):
		"""Повертає список незамаплених співробітників."""
		mapped_old = frappe.get_all("oiEmployeeMapping", pluck="old_employee")

		unmapped = frappe.get_all(
			"oiEmployee",
			filters={"name": ["not in", mapped_old]} if mapped_old else {},
			fields=["name", "full_name", "organization", "user"],
			order_by="full_name",
		)

		# Додаємо можливі збіги з hromsEmployee
		for emp in unmapped:
			# Шукаємо можливий збіг за ПІБ
			possible_match = frappe.db.get_value(
				"hromsEmployee",
				{"full_name": emp.full_name},
				["name", "full_name", "department"],
				as_dict=True,
			)
			emp["possible_match"] = possible_match

		return unmapped

	@frappe.whitelist()
	def get_unmapped_organizations(self):
		"""Повертає список незамаплених організацій."""
		mapped_old = frappe.get_all("oiOrganizationMapping", pluck="old_organization")

		unmapped = frappe.get_all(
			"oiOrganization",
			filters={"name": ["not in", mapped_old]} if mapped_old else {},
			fields=["name", "organization_name", "tax_code"],
			order_by="organization_name",
		)

		# Додаємо можливі збіги з hromsOrgStructure
		for org in unmapped:
			# Шукаємо можливий збіг за назвою або ЄДРПОУ
			possible_match = None

			if org.tax_code:
				possible_match = frappe.db.get_value(
					"hromsOrgStructure",
					{"tax_code": org.tax_code},
					["name", "department_name", "tax_code"],
					as_dict=True,
				)

			if not possible_match and org.organization_name:
				possible_match = frappe.db.get_value(
					"hromsOrgStructure",
					{"department_name": org.organization_name},
					["name", "department_name", "tax_code"],
					as_dict=True,
				)

			org["possible_match"] = possible_match

		return unmapped

	@frappe.whitelist()
	def create_employee_mapping(self, old_employee, new_employee):
		"""Створює mapping для одного співробітника."""
		if frappe.db.exists("oiEmployeeMapping", {"old_employee": old_employee}):
			frappe.throw(f"Mapping для {old_employee} вже існує")

		doc = frappe.get_doc(
			{
				"doctype": "oiEmployeeMapping",
				"old_employee": old_employee,
				"new_employee": new_employee,
			}
		)
		doc.insert()
		self.refresh_status()
		return {"status": "success", "name": doc.name}

	@frappe.whitelist()
	def create_organization_mapping(self, old_organization, new_organization):
		"""Створює mapping для однієї організації."""
		if frappe.db.exists("oiOrganizationMapping", {"old_organization": old_organization}):
			frappe.throw(f"Mapping для {old_organization} вже існує")

		doc = frappe.get_doc(
			{
				"doctype": "oiOrganizationMapping",
				"old_organization": old_organization,
				"new_organization": new_organization,
			}
		)
		doc.insert()
		self.refresh_status()
		return {"status": "success", "name": doc.name}
