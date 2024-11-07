# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
import json



class GenerateSalesInvoice(Document):
	
	def before_save(self):

		values = {
			"start_date": self.start_date,
			"end_date": self.end_date,
			"station": self.station,
			"billing_type": self.billing_type,
			"icris_number": self.icris_number,
			"customer":self.customer,
			"import__export" : self.import__export
		}

		# Begin the SQL query
		query = """
			SELECT 
				shipment_number
			FROM 
				`tabShipment Number` as sn
			WHERE
				sn.date_shipped BETWEEN %(start_date)s AND %(end_date)s
		"""

		# Initialize a list for conditions
		conditions = []

		# Add conditions dynamically based on provided values
		if values["station"]:
			conditions.append("sn.station = %(station)s")
		if values["billing_type"]:
			conditions.append("sn.billing_type = %(billing_type)s")
		if values["icris_number"]:
			conditions.append("sn.icris_number = %(icris_number)s")
		if values["import__export"]:
			conditions.append("sn.import__export = %(import__export)s")
		if values["customer"]:
			conditions.append("sn.customer = %(customer)s")

		# If there are additional conditions, join them to the query
		if conditions:
			query += " AND " + " AND ".join(conditions)

		# Execute the query with the provided values
		results = frappe.db.sql(query, values)
		shipment_numbers = [row[0] for row in results]
		self.total_shipment_numbers = len(shipment_numbers)
		self.shipment_numbers = ', '.join(shipment_numbers)
		self.shipment_numbers_and_sales_invoices = []
		for i in shipment_numbers:
			self.append('shipment_numbers_and_sales_invoices', {
				'shipment_number': i  # Replace 'shipment_number' with the actual field name in your child table
			})
		
	
	 