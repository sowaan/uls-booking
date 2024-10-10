# Copyright (c) 2024, fariz.khanzada@sowaan.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class R300000(Document):
      pass
	# def before_save(self):
            
		# setting = frappe.get_doc("Manifest Setting Definition")

		# # for i in setting.manifest_setting:
		# # 	if i.record == self.name:
		# # 		field_value = getattr(self, i.field_name, None)
		# # 		if field_value == i.code:
		# # 			setattr(self, i.field_name, i.replacement)




		# country_map = {j.code: j.country for j in setting.country_codes}

		# doctype = self.doctype

        # # Iterate over field names and records
		# for field_info in setting.field_names_and_records:
		# 	if field_info.record == doctype:
		# 		field_value = getattr(self, field_info.field_name, None)
		# 		# Only set the attribute if the field value exists in the country map
		# 		if field_value in country_map:
		# 			# Directly set the country name if found
		# 			setattr(self, field_info.field_name, country_map[field_value])
				