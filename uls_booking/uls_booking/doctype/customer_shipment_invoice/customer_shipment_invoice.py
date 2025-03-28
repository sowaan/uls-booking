# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime


class CustomerShipmentInvoice(Document):
	def autoname(self):
		pdf_values = frappe.db.get_value(
            'Sales Invoice PDF', 
            self.sales_invoice_pdf, 
            ['import__export', 'station'], 
            as_dict=True
        )
		prefix = "AAA"
		station = "0"
		serial = '00001'
		if pdf_values:

			if pdf_values.get('import__export') == "Import":
				prefix = "IFC"
			elif pdf_values.get('import__export') == "Export":
				prefix = "EPP"
			station_map = {
				"karachi": "1",
				"lahore": "2",
				"islamabad": "3",
				"sialkot": "4",
				"faisalabad": "5",
				"peshawar": "6"
			}
			station = station_map.get((pdf_values.get("station") or "").lower(), "0")




		last_invoice_name = frappe.db.get_value("Customer Shipment Invoice", {}, "name", order_by="creation DESC")
		current_year = datetime.today().strftime("%y")
		current_month = datetime.today().strftime("%m")
		if last_invoice_name:
			if "-" in last_invoice_name:
				parts = last_invoice_name.split("-")
				if len(parts) == 3:
					serial_with_dates = parts[-1]
					pre_year = serial_with_dates[:2]
					if pre_year == current_year:
						serial = serial_with_dates[4:]
						if serial.isdigit():
							serial = str(int(serial) + 1).zfill(5)
				
		
		self.name = f"{prefix}-{station}-{current_year}{current_month}{serial}"
		

