# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PostalCodeCreationTool(Document):
	# pass


	# def before_insert(self) :

	# 	from_range = str(self.from_range)
	# 	to_range = str(self.to_range)
	# 	country = self.country

	# 	if self.add_prefix :
	# 		from_range = str(self.prefix) + from_range
	# 		to_range = str(self.prefix) + to_range

	# 	if self.add_suffix :
	# 		from_range = from_range + str(self.suffix)
	# 		to_range = to_range + str(self.suffix)

	# 	self.naming_series = from_range	+ "-" + to_range + "-" + country + "-"







	def before_save(self) :

		if self.from_range < 0 or self.to_range < 0 :
			frappe.throw("Ranges cannot be Negative.")
		if self.from_range > self.to_range :
			frappe.throw("'From Range' cannot be greater than 'To Range'")

		# from_range = str(self.from_range)
		# to_range = str(self.to_range)
		# country = self.country

		# if self.add_prefix :
		# 	from_range = str(self.prefix) + from_range
		# 	to_range = str(self.prefix) + to_range

		# if self.add_suffix :
		# 	from_range = from_range + str(self.suffix)
		# 	to_range = to_range + str(self.suffix)

		# self.naming_series = from_range	+ "-" + to_range + "-" + country + "-"	

		


	# def after_save(self) :
	# 	from_range = str(self.from_range)
	# 	to_range = str(self.to_range)
	# 	country = self.country

	# 	if self.add_prefix :
	# 		from_range = str(self.prefix) + from_range
	# 		to_range = str(self.prefix) + to_range

	# 	if self.add_suffix :
	# 		from_range = from_range + str(self.suffix)
	# 		to_range = to_range + str(self.suffix)

	# 	self.naming_series = from_range	+ "-" + to_range + "-" + country + "-"	





	def before_submit(self) :
		from_range = int(self.from_range)	
		to_range = int(self.to_range)	
		area = self.area
		country = self.country
		# city = self.city


		while from_range <= to_range:
			postal_code = str(from_range)

			if self.add_prefix :
				postal_code = str(self.prefix) + postal_code

			if self.add_suffix :
				postal_code = postal_code + str(self.suffix)

			db_rec = frappe.db.exists({"doctype": "Postal Codes", "postal_code": postal_code , "country":country })
			# frappe.msgprint(str(db_rec))

			if db_rec :
				frappe.db.set_value("Postal Codes",db_rec,"area",area)
				frappe.db.set_value("Postal Codes",db_rec,"postal_code_creation_tool",self.name)
				

			else :	

				postal_code_doc = frappe.get_doc({
					'doctype' : 'Postal Codes',
					'postal_code' : postal_code,
					'area' : area,
					# 'city' : city,
					'country' : country,
					'postal_code_creation_tool' : self.name
				})
				postal_code_doc.insert()
			from_range = from_range + 1
	


	# def before_cancel(self) :

	# 	postal_code_list = frappe.get_list("Postal Codes",
	# 		                    filters={
	# 								'postal_code_creation_tool' : self.name ,
	# 						})
	# 	if postal_code_list :
	# 		for pc in postal_code_list :
	# 			pc_doc = frappe.get_doc("Postal Codes",pc.name)
	# 			pc_doc.delete()				
