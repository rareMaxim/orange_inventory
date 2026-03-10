# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe


def get_manufacturer_from_mac(mac: str) -> str | None:
	"""
	Визначає виробника за MAC-адресою (OUI).
	"""
	if not mac:
		return None

	# База OUI (Організаційно унікальних ідентифікаторів)
	# Перші 3 байти MAC-адреси
	prefix = mac.replace(":", "").replace("-", "").upper()[:6]

	oui_db = {
		"18FD74": "MikroTik",
		"4C5E0C": "MikroTik",
		"D4CA6D": "MikroTik",
		"E48D8C": "MikroTik",
		"000048": "Seiko Epson",
		"000085": "Canon",
		"001708": "Hewlett Packard",
		"001871": "Hewlett Packard",
		"001E0B": "Hewlett Packard",
		"8C38AD": "Netgear",
		"000FB5": "Intel",
		"F86926": "Cloud Network Technology (Singapore)",
		"1081DF": "Cloud Network Technology (Singapore)",
		"4E6666": "Cloud Network Technology (Singapore)",
		"F889D2": "Cloud Network Technology (Singapore)",
		"FCF8AE": "Apple",
		"000393": "Apple",
		"0010FA": "Apple",
		"0016CB": "Apple",
		"0017F2": "Apple",
		"0019E3": "Apple",
		"001B63": "Apple",
		"001C11": "Apple",
		"001C43": "Apple",
		"001C4F": "Apple",
		"001C5D": "Apple",
		"001D4F": "Apple",
		"001E52": "Apple",
		"001E85": "Apple",
		"001E8F": "Apple",
		"001F3B": "Apple",
		"001F5B": "Apple",
		"001F5C": "Apple",
		"001F5F": "Apple",
		"001FF3": "Apple",
		"001FFD": "Apple",
		"00215C": "Apple",
		"0021E9": "Apple",
		"002312": "Apple",
		"002332": "Apple",
		"00236C": "Apple",
		"0023DF": "Apple",
		"002436": "Apple",
		"002500": "Apple",
		"00254B": "Apple",
		"0025B3": "Apple",
		"0025BC": "Apple",
		"002608": "Apple",
		"00264A": "Apple",
		"0026B0": "Apple",
		"0026BB": "Apple",
		"28CFDA": "Apple",
		"78CA39": "Apple",
		"A44E31": "Apple",
		"CC25EF": "Apple",
		"D023DB": "Apple",
		"D83062": "Apple",
		"F0761C": "Apple",
		"F82793": "Apple",
		"DC2F12": "TP-Link",
		"E8DE27": "TP-Link",
		"F4F26D": "TP-Link",
		"000C29": "VMware",
		"000569": "VMware",
		"005056": "VMware",
		"080027": "Oracle (VirtualBox)",
		"BC5FF4": "ASRock",
		"D8CB8A": "MSI",
		"4CCC6A": "Samsung",
		"D890E8": "Samsung",
		"001599": "Samsung",
		"001B98": "Samsung",
		"001D28": "Samsung",
		"001ECC": "Samsung",
		"002490": "Samsung",
		"002637": "Samsung",
		"303855": "Samsung",
		"382D15": "Samsung",
		"4044FD": "Samsung",
		"44F459": "Samsung",
		"50568B": "Samsung",
		"5083B5": "Samsung",
		"50CCF8": "Samsung",
		"54E499": "Samsung",
		"5C5B5F": "Samsung",
		"5C7E61": "Samsung",
		"60A10A": "Samsung",
		"60D02C": "Samsung",
		"64B310": "Samsung",
		"702C1F": "Samsung",
		"706BD8": "Samsung",
		"78216A": "Samsung",
		"8421EE": "Samsung",
		"84742A": "Samsung",
		"88308A": "Samsung",
		"945103": "Samsung",
		"9463D1": "Samsung",
		"A4DD39": "Samsung",
		"B407F9": "Samsung",
		"B4ED2B": "Samsung",
		"B827EB": "Raspberry Pi",
		"D0FF50": "Raspberry Pi",
		"F05101": "Ubiquiti",
		"802AA8": "Ubiquiti",
		"24A43C": "Ubiquiti",
	}

	manufacturer_name = oui_db.get(prefix)
	if not manufacturer_name:
		return None

	# Перевіряємо чи є такий виробник у системі
	if not frappe.db.exists("oiManufacturer", manufacturer_name):
		# Створюємо нового виробника
		m = frappe.new_doc("oiManufacturer")
		m.manufacturer_name = manufacturer_name
		m.insert(ignore_permissions=True)
		return m.name

	return frappe.db.get_value("oiManufacturer", {"manufacturer_name": manufacturer_name}, "name")
