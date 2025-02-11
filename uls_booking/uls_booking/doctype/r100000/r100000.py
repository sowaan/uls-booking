# Copyright (c) 2024, fariz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from uls_booking.uls_booking.api.sales_invoice_script import generate_single_invoice

class R100000(Document):
	# def before_save(self):
		# customer_doc = frappe.get_doc("Customer","NORTH POLE LAHORE")
		# context = {
		# 		"customer": customer_doc
		# 	}
		# condition = "customer.custom_allow_direct_delivery_only and True"
		# result = frappe.safe_eval(condition,context)
		# frappe.msgprint(str(result))
    # pass
	def before_save(self):
		shipment_number = "X3W337NFFLJ"
		sales_invoice_definition = "Default"
		end_date = "2024-07-11"
		generate_single_invoice(shipment_number,sales_invoice_definition,end_date)
		# sales_invoice = frappe.get_doc("Sales Invoice",{"custom_shipment_number":shipment_number , "custom_freight_invoices": 1})
		# frappe.db.set_value("Sales Invoice", sales_invoice.name, "custom_freight_invoices", 0)
		# # sales_invoice.custom_freight_invoices = 0

		# frappe.db.set_value("Sales Invoice", sales_invoice.name, "custom_compensation_invoices", 1)
		# # sales_invoice.custom_freight_invoices = 1
		# sales_invoice.save()
		# frappe.db.commit()