# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FullTariff(Document):
	# pass
	def before_save(self) :
		if self.based_on == 'Country' :
			self.zone = None
			country_name_list = frappe.get_list('Country Names' , 
									filters={
										'countries' : self.country ,
										'parenttype' : 'Zone'
									},
									fields = ['*'],
									ignore_permissions=True
								)
			if country_name_list :
				for row in country_name_list :
					zone_doc = frappe.get_doc("Zone",row.parent)
					if zone_doc.is_single_country != 1 :
						self.zone = zone_doc.name
						break
						
