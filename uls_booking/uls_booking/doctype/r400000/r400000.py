# Copyright (c) 2024, fariz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class R400000(Document):
    # pass
	def before_save(self):
		self.consignee_city = self.consignee_city.capitalize()
		
				