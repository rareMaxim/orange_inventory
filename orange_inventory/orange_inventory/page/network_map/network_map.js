frappe.pages["network-map"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Карта Мережі",
		single_column: true,
	});

	// Додаємо контейнер для карти
	let container = $(
		'<div id="network-map-container" style="height: 70vh; border: 1px solid #d1d8dd; border-radius: 4px;"></div>'
	).appendTo(page.body);

	// Функція для завантаження скриптів
	function load_script(url) {
		return new Promise((resolve, reject) => {
			let script = document.createElement("script");
			script.type = "text/javascript";
			script.src = url;
			script.onload = resolve;
			script.onerror = reject;
			document.head.appendChild(script);
		});
	}

	// Функція для завантаження стилів
	function load_css(url) {
		let link = document.createElement("link");
		link.rel = "stylesheet";
		link.type = "text/css";
		link.href = url;
		document.head.appendChild(link);
	}

	function render_map() {
		// Завантажуємо дані та будуємо карту

		frappe.call({
			method: "orange_inventory.network_map.get_network_graph_data",
			callback: function (r) {
				if (r.message) {
					/* global vis */
					let nodes = new vis.DataSet(r.message.nodes);
					let edges = new vis.DataSet(r.message.edges);

					let data = {
						nodes: nodes,
						edges: edges,
					};

					let options = {
						nodes: {
							shape: "box",
							font: { size: 14, face: "arial" },
							margin: 10,
							color: {
								border: "#6ab7ff",
								background: "#eaf5ff",
								highlight: {
									border: "#1a8cff",
									background: "#d4eaff",
								},
							},
						},
						edges: {
							font: { align: "middle", size: 12, color: "#555" },
							arrows: { to: { enabled: false }, from: { enabled: false } },
							color: {
								color: "#848484",
								highlight: "#2B7CE9",
								hover: "#2B7CE9",
							},
						},
						physics: {
							enabled: true,
							solver: "barnesHut",
							barnesHut: { gravitationalConstant: -4000 },
						},
						interaction: { hover: true, tooltipDelay: 200 },
					};

					let network = new vis.Network(container[0], data, options);

					network.on("doubleClick", function (params) {
						if (params.nodes.length > 0) {
							let nodeId = params.nodes[0];
							frappe.set_route("Form", "oiAsset", nodeId);
						}
					});
				} else {
					container.html(
						'<div class="text-center" style="padding: 20px;">Немає даних для відображення.</div>'
					);
				}
			},
		});
	}

	// Спочатку завантажуємо стилі, потім скрипт, а потім рендеримо карту
	load_css("https://unpkg.com/vis-network/styles/vis-network.min.css");
	load_script("https://unpkg.com/vis-network/standalone/umd/vis-network.min.js")
		.then(() => {
			render_map(); // Запускаємо рендер тільки після успішного завантаження
		})
		.catch(() => {
			frappe.msgprint(__("Не вдалося завантажити бібліотеку для візуалізації мережі."));
		});
};
