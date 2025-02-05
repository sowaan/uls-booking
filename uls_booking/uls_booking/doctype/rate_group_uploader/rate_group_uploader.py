# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RateGroupUploader(Document):
	
	
	def before_save(self) :

		unique_accounts = set()
		unique_rows = []

		for row in self.icris_account_table :

			if row.icris_account not in unique_accounts :

				unique_accounts.add(row.icris_account)
				unique_rows.append(row)

		self.icris_account_table = []
		self.icris_account_table = unique_rows















	def before_submit(self) :

		if self.rate_group_type == "Selling Rate Group" :
			
			for row in self.icris_account_table :
				icris_acc_doc = frappe.get_doc("ICRIS Account" , row.icris_account)
				sig = 0
				for x in icris_acc_doc.rate_group :
					if x.rate_group == self.rate_group :

						x.from_date = self.from_date
						x.to_date = self.to_date
						icris_acc_doc.save()
						sig =1
						break

				if sig == 0 :
					icris_acc_doc.append('rate_group',{
						'rate_group' : self.rate_group ,
						'from_date' : self.from_date ,
						'to_date' : self.to_date ,
					})
					icris_acc_doc.save()
			






		elif self.rate_group_type == "Buying Rate Group" :
			
			for row in self.icris_account_table :
				icris_acc_doc = frappe.get_doc("ICRIS Account" , row.icris_account)


				sig1 = 0
				for y in icris_acc_doc.buying_rate_group :
					if y.rate_group == self.rate_group :
						y.from_date = self.from_date
						y.to_date = self.to_date
						icris_acc_doc.save()
						sig1 =1
						break



				if sig1 == 0 :
					icris_acc_doc.append('buying_rate_group',{
						'rate_group' : self.rate_group ,
						'from_date' : self.from_date ,
						'to_date' : self.to_date ,
					})
					icris_acc_doc.save()





