# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe.model.document import Document


class oiCommandTemplate(Document):
	def validate(self):
		self.validate_parameters_json()
		self.validate_command_template()

	def validate_parameters_json(self):
		"""Перевіряє що allowed_parameters є валідним JSON."""
		if not self.allowed_parameters:
			return

		try:
			params = json.loads(self.allowed_parameters)
			if not isinstance(params, dict):
				frappe.throw("allowed_parameters повинен бути JSON об'єктом")

			# Перевіряємо структуру кожного параметра
			for param_name, param_config in params.items():
				if not isinstance(param_config, dict):
					frappe.throw(f"Конфігурація параметра '{param_name}' повинна бути об'єктом")

				# Перевіряємо що pattern є валідним regex
				if "pattern" in param_config:
					try:
						re.compile(param_config["pattern"])
					except re.error as e:
						frappe.throw(f"Невалідний regex pattern для '{param_name}': {e}")

		except json.JSONDecodeError as e:
			frappe.throw(f"Невалідний JSON в allowed_parameters: {e}")

	def validate_command_template(self):
		"""Перевіряє що всі параметри в шаблоні описані."""
		if not self.command_template:
			return

		# Знаходимо всі {param} в шаблоні
		template_params = set(re.findall(r"\{(\w+)\}", self.command_template))

		if not template_params:
			return  # Немає параметрів - OK

		if not self.allowed_parameters:
			frappe.throw("Шаблон містить параметри, але allowed_parameters не заповнено")

		try:
			allowed = set(json.loads(self.allowed_parameters).keys())
		except (json.JSONDecodeError, AttributeError):
			allowed = set()

		missing = template_params - allowed
		if missing:
			frappe.throw(f"Параметри {missing} використані в шаблоні, але не описані в allowed_parameters")

	def render_command(self, parameters: dict) -> str:
		"""
		Рендерить команду з параметрами.

		Args:
		    parameters: словник з параметрами

		Returns:
		    str: готова команда

		Raises:
		    frappe.ValidationError: якщо параметри не проходять валідацію
		"""
		if not self.allowed_parameters:
			# Немає параметрів - повертаємо шаблон як є
			return self.command_template

		allowed_params = json.loads(self.allowed_parameters)

		# Валідуємо кожен переданий параметр
		for param_name, param_value in parameters.items():
			if param_name not in allowed_params:
				frappe.throw(f"Невідомий параметр: {param_name}", frappe.ValidationError)

			param_config = allowed_params[param_name]

			# Перевірка типу
			param_type = param_config.get("type", "string")
			if param_type == "string" and not isinstance(param_value, str):
				frappe.throw(f"Параметр '{param_name}' повинен бути строкою", frappe.ValidationError)
			elif param_type == "int" and not isinstance(param_value, int):
				frappe.throw(f"Параметр '{param_name}' повинен бути числом", frappe.ValidationError)

			# Перевірка pattern
			if "pattern" in param_config and isinstance(param_value, str):
				if not re.match(param_config["pattern"], param_value):
					frappe.throw(
						f"Параметр '{param_name}' не відповідає дозволеному формату",
						frappe.ValidationError,
					)

			# Перевірка allowed_values
			if "allowed_values" in param_config:
				if param_value not in param_config["allowed_values"]:
					frappe.throw(
						f"Значення '{param_value}' не дозволено для параметра '{param_name}'",
						frappe.ValidationError,
					)

			# Перевірка max_length
			if "max_length" in param_config and isinstance(param_value, str):
				if len(param_value) > param_config["max_length"]:
					frappe.throw(
						f"Параметр '{param_name}' занадто довгий (макс {param_config['max_length']})",
						frappe.ValidationError,
					)

		# Рендеримо команду
		try:
			return self.command_template.format(**parameters)
		except KeyError as e:
			frappe.throw(f"Відсутній обов'язковий параметр: {e}", frappe.ValidationError)
