// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

// frappe.ui.form.on("oiHromadaSurvey", {
// 	refresh(frm) {

// 	},
// });
// qms_cherga / orange_inventory шлях підкоригуй під свій app
frappe.ui.form.on("oiHromadaSurvey", {
	onload(frm) {
		// update_value_display(frm);
	},
	refresh(frm) {
		if (frm.doc.type == "Група") {
			frm.add_custom_button("Recompute Group Scores", async () => {
				await frappe.call({
					method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.recompute_group_scores",
					args: { root: frm.doc.name },
				});
				await frm.reload_doc();
				frappe.show_alert({ message: "Scores recomputed", indicator: "green" });
			});
		} else if (!frm.is_new()) {
			// Кнопка для показу графіка тренду
			frm.add_custom_button(__("Показати Тенденцію"), function () {
				show_value_trend_chart(frm);
			});
		}
	},
	type(frm) {
		update_value_display(frm);
	},
	bool_data(frm) {
		update_value_display(frm);
	},
	int_data(frm) {
		update_value_display(frm);
	},
	validate(frm) {
		update_value_display(frm);
	},
});

function update_value_display(frm) {
	if (frm.doc.type == "Група") {
		// Для вузлів-груп не показуємо значення
		frm.set_value("value_display", "");
		frm.set_value("is_group", 1);
		return;
	}

	const t = frm.doc.type;
	if (t === "Якісні дані") {
		// Показувати як Так/Ні (або 1/0 — вибери)
		const v = cint(frm.doc.bool_data) ? "Так" : "Ні";
		frm.set_value("value_display", v);
	} else if (t === "Кількісні дані") {
		frm.set_value("value_display", frm.doc.int_data ?? "0");
	} else {
		frm.set_value("value_display", "");
	}
}

function show_value_trend_chart(frm) {
	frappe.call({
		method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.get_value_trend_data",
		args: {
			survey_id: frm.doc.name,
			limit: 50,
		},
		callback: function (r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				const data = r.message;

				// Створюємо діалог з графіком
				let d = new frappe.ui.Dialog({
					title: __("Тенденція: {0}", [data.title]),
					size: "large",
					fields: [
						{
							fieldname: "chart_html",
							fieldtype: "HTML",
						},
					],
				});

				d.show();

				// Створюємо Chart.js графік
				const chart_wrapper = d.fields_dict.chart_html.$wrapper;
				chart_wrapper.html(`
					<div style="padding: 20px;">
						<canvas id="trend-chart-${frm.doc.name}"></canvas>
					</div>
				`);

				// Завантажуємо Chart.js якщо ще не завантажено
				const render_chart = () => {
					const ctx = document
						.getElementById(`trend-chart-${frm.doc.name}`)
						.getContext("2d");

					new Chart(ctx, {
						type: "line",
						data: {
							labels: data.labels,
							datasets: [
								{
									label: data.title,
									data: data.values,
									borderColor: "rgb(75, 192, 192)",
									backgroundColor: "rgba(75, 192, 192, 0.2)",
									tension: 0.1,
									fill: true,
								},
							],
						},
						options: {
							responsive: true,
							maintainAspectRatio: true,
							plugins: {
								title: {
									display: true,
									text: `${data.title} (${data.frequency})`,
								},
								legend: {
									display: true,
								},
							},
							scales: {
								y: {
									beginAtZero: true,
									title: {
										display: true,
										text:
											data.type === "Кількісні дані"
												? "Значення"
												: "% (Так=100, Ні=0)",
									},
								},
								x: {
									title: {
										display: true,
										text: "Період",
									},
								},
							},
						},
					});
				};

				if (typeof Chart === "undefined") {
					frappe.require("assets/frappe/js/lib/chart.min.js", render_chart);
				} else {
					render_chart();
				}
			} else {
				frappe.msgprint({
					title: __("Немає даних"),
					message: __(
						"Історія змін для цього показника ще не накопичена. Змініть значення кілька разів для відстеження тенденції."
					),
					indicator: "orange",
				});
			}
		},
	});
}
