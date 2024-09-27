# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from uls_booking.uls_booking.api.api import (check_for_existing_rate , create_rate)


class RateCreationTool(Document):
	def before_save(self):
		full_tariff = frappe.get_doc('Full Tariff', self.full_tariff)
		valid = True
		prev_to_weight = 0


		if self.weight_slab[0].from_weight > full_tariff.package_rate[0].weight:
			valid = False
			frappe.throw(f"The From Weight in the first row must be less than or equal to the Weight of the first row in Package Rate of {self.full_tariff}.")


		if self.weight_slab[-1].to_weight < full_tariff.package_rate[-1].weight:
			valid = False
			frappe.throw(f"The To Weight in the last row must be greater than or equal to the Weight of the last row in Package Rate of {self.full_tariff}.")


		for idx, row in enumerate(self.weight_slab):
			if idx > 0:
				if row.from_weight != prev_to_weight + 0.5:
					valid = False
					frappe.throw(f"Row {idx + 1}: From Weight must be 0.5 greater than To Weight of the previous row.")
			prev_to_weight = row.to_weight

 

	def before_submit(self):

		if self.select_rate_type == 'Selling Rate' :
			create_rate(self.full_tariff , self.weight_slab , self.select_rate_type, self.selling_rate_group, self.name )


		elif self.select_rate_type == 'Buying Rate' :
			create_rate(self.full_tariff , self.weight_slab , self.select_rate_type, self.buying_rate_group, self.name )


