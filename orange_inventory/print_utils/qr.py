import base64
import io

import frappe
import qrcode


@frappe.whitelist()
def png_data_uri(value: str, box_size: int = 5, border: int = 0):
	qr = qrcode.QRCode(box_size=int(box_size), border=int(border))
	qr.add_data(value or "")
	qr.make(fit=True)
	img = qr.make_image(fill_color="black", back_color="white")
	buf = io.BytesIO()
	img.save(buf, format="PNG")
	return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
