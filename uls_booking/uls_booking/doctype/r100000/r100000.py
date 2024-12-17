# Copyright (c) 2024, fariz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from uls_booking.uls_booking.api.sales_invoice_script import generate_single_invoice

class R100000(Document):
    pass
	# def before_save(self):
	# 	shipment_number = "W7W637FLZR9"
	# 	sales_invoice_definition = "Default"
	# 	end_date = "2024-07-11"
	# 	generate_single_invoice(shipment_number,sales_invoice_definition,end_date)
