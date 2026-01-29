# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Білд агента з Frappe.

Використання:
    bench --site {site} execute orange_inventory.build_agent.build
    bench --site {site} execute orange_inventory.build_agent.build_and_release
"""

import hashlib
import os
import re
import subprocess

import frappe
from frappe.utils import get_bench_path


def get_agent_dir():
	"""Повертає шлях до директорії агента."""
	return os.path.join(get_bench_path(), "apps", "orange_inventory", "agent")


def get_agent_version():
	"""Отримує версію агента з коду."""
	agent_file = os.path.join(get_agent_dir(), "orange_agent.go")
	with open(agent_file) as f:
		content = f.read()

	match = re.search(r'AppVersion\s*=\s*"([^"]+)"', content)
	if match:
		return match.group(1)
	return "unknown"


def build(target_os: str = "windows", target_arch: str = "amd64"):
	"""
	Збирає агента.

	Args:
	        target_os: цільова ОС (windows, linux, darwin)
	        target_arch: архітектура (amd64, 386, arm64)

	Returns:
	        dict: {"success": True, "path": "...", "size": 123, "version": "1.2"}
	"""
	agent_dir = get_agent_dir()
	version = get_agent_version()

	# Формуємо ім'я файлу
	ext = ".exe" if target_os == "windows" else ""
	output_name = f"orange_agent_{version}_{target_os}_{target_arch}{ext}"
	output_path = os.path.join(agent_dir, output_name)

	# Запускаємо go mod tidy
	print("Running go mod tidy...")
	result = subprocess.run(["go", "mod", "tidy"], cwd=agent_dir, capture_output=True, text=True)
	if result.returncode != 0:
		return {"success": False, "error": f"go mod tidy failed: {result.stderr}"}

	# Запускаємо білд
	print(f"Building agent v{version} for {target_os}/{target_arch}...")
	env = os.environ.copy()
	env["GOOS"] = target_os
	env["GOARCH"] = target_arch
	env["CGO_ENABLED"] = "0"

	result = subprocess.run(
		["go", "build", "-ldflags=-s -w", "-o", output_path, "orange_agent.go"],
		cwd=agent_dir,
		capture_output=True,
		text=True,
		env=env,
	)

	if result.returncode != 0:
		return {"success": False, "error": f"Build failed: {result.stderr}"}

	# Отримуємо розмір файлу
	file_size = os.path.getsize(output_path)

	print(f"✓ Build successful: {output_name} ({file_size / 1024 / 1024:.2f} MB)")

	return {
		"success": True,
		"path": output_path,
		"filename": output_name,
		"size": file_size,
		"version": version,
	}


def build_and_release(target_os: str = "windows", target_arch: str = "amd64", is_latest: bool = True):
	"""
	Збирає агента і створює реліз у Frappe.

	Args:
	        target_os: цільова ОС
	        target_arch: архітектура
	        is_latest: позначити як актуальну версію

	Returns:
	        dict: {"success": True, "release": "1.2", "download_url": "..."}
	"""
	# Спочатку білдимо
	build_result = build(target_os, target_arch)
	if not build_result["success"]:
		return build_result

	version = build_result["version"]
	file_path = build_result["path"]

	# Перевіряємо чи вже існує такий реліз
	if frappe.db.exists("oiAgentRelease", version):
		print(f"Release {version} already exists, updating...")
		release = frappe.get_doc("oiAgentRelease", version)
	else:
		print(f"Creating new release {version}...")
		release = frappe.new_doc("oiAgentRelease")
		release.version = version

	# Завантажуємо файл
	with open(file_path, "rb") as f:
		file_content = f.read()

	# Обчислюємо checksum
	checksum = hashlib.sha256(file_content).hexdigest()

	# Створюємо File document
	file_doc = frappe.get_doc(
		{"doctype": "File", "file_name": build_result["filename"], "is_private": 1, "content": file_content}
	)
	file_doc.save(ignore_permissions=True)

	# Оновлюємо реліз
	release.agent_file = file_doc.file_url
	release.file_checksum = checksum
	release.file_size = build_result["size"]
	release.is_latest = is_latest
	release.release_date = frappe.utils.today()
	release.save(ignore_permissions=True)

	frappe.db.commit()

	# Видаляємо локальний файл
	os.remove(file_path)

	print(f"✓ Release {version} created successfully!")
	print(f"  Checksum: {checksum[:16]}...")
	print(f"  Size: {build_result['size'] / 1024 / 1024:.2f} MB")

	return {"success": True, "release": version, "checksum": checksum, "size": build_result["size"]}


@frappe.whitelist()
def api_build_and_release():
	"""API endpoint для білду і релізу (для виклику з UI)."""
	frappe.only_for("System Manager")
	return build_and_release()
