// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("Orange Inventory Settings", {
	refresh(frm) {
		// Додаємо обробник для кнопки генерації ключа
		frm.fields_dict.regenerate_key_button.$input.on("click", function () {
			frappe.confirm(
				__(
					"Згенерувати новий ключ підпису команд?<br><br>" +
						"<b>Увага:</b> Після цього потрібно оновити ключ у config.json на всіх агентах!"
				),
				function () {
					// Yes
					frm.call({
						method: "generate_signing_key",
						doc: frm.doc,
						freeze: true,
						freeze_message: __("Генерація ключа..."),
						callback: function (r) {
							if (r.message && r.message.key) {
								frm.reload_doc();
								frappe.msgprint({
									title: __("Ключ згенеровано"),
									indicator: "green",
									message: __(
										"Новий ключ підпису успішно згенеровано.<br><br>" +
											"<b>Скопіюйте цей ключ у config.json агентів:</b><br>" +
											"<code style='user-select: all; display: block; padding: 10px; " +
											"background: var(--bg-color); border-radius: 4px; margin-top: 10px;'>" +
											r.message.key +
											"</code>"
									),
								});
							}
						},
					});
				}
			);
		});
	},
});
