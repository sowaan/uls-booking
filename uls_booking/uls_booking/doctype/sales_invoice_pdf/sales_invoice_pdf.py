# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class SalesInvoicePDF(Document):
	def before_save(self):

		values = {
			"start_date": self.start_date,
			"end_date": self.end_date,
			"station": self.station,
			"icris_number": self.icris_number,
			"customer": self.customer
		}

		# Begin the SQL query
		query = """
			SELECT 
				si.name,
				si.custom_shipment_number
			FROM 
				`tabSales Invoice` as si
			LEFT JOIN
				`tabShipment Number` as sn ON si.custom_shipment_number = sn.name
			WHERE
				sn.date_shipped BETWEEN %(start_date)s AND %(end_date)s 
				AND si.customer = %(customer)s
				AND si.docstatus = 1
		"""

		# Initialize a list for conditions
		conditions = []

		# Add conditions dynamically based on provided values
		if values["station"]:
			conditions.append("sn.station = %(station)s")
		if values["icris_number"]:
			conditions.append("sn.icris_number = %(icris_number)s")
		
		# If there are additional conditions, join them to the query
		if conditions:
			query += " AND " + " AND ".join(conditions)

		# Execute the query with the provided values
		results = frappe.db.sql(query, values)
		sales_invoices = [row[0] for row in results]
		self.total_invoices = len(sales_invoices)
		self.sales_invoices = ', '.join(sales_invoices)
