# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class DutyandTaxesSalesInvoiceUploader(Document):
	# pass



	@frappe.whitelist()	
	def get_dtt(self) :
		
		date = None
		mawb_number = None
		flight_number = None
		typ = None
		mno = None

		if self.date :
			date = self.date
		if self.mawb_number :
			mawb_number = self.mawb_number
		if self.date :
			flight_number = self.flight_number
		if self.type :
			typ = self.type
		if self.mno :
			mno = self.mno

		result = frappe.db.sql(
            """
            select name, tracking_number, docstatus, invoiced, shipment_number from `tabDuty and Taxes Template`
            where ( date LIKE %(date)s or %(date)s is null )
            and ( mawb_number LIKE %(mawb_number)s or %(mawb_number)s is null )
            and ( flight_number LIKE %(flight_number)s or %(flight_number)s is null )
            and ( type LIKE %(type)s or %(type)s is null )
            and ( mno LIKE %(mno)s or %(mno)s is null )
            """,
            {"date": date, "mawb_number": mawb_number, "flight_number": flight_number, "type": typ, "mno": mno},
        )


		return result
		


	def before_save(self) :


		if not self.date and not self.mawb_number and not self.flight_number and not self.type and not self.mno :
			frappe.throw("Please Fill atleast one filter.")

		result = self.get_dtt()
		count = 0

		self.set('duty_and_taxes_template', [])

		if result :
			for i in range(len(result)) :
				if result[i][2] == 1 and result[i][3] == 0 :
					row = {
						"duty_and_taxes_template": result[i][0],
						"tracking_number": result[i][1],
						"shipment_number": result[i][4],
					}
					self.append('duty_and_taxes_template', row)
					count = count + 1
		self.number_of_dtt_fetched = count
		


	def validate(self) :
		self.flags.ignore_links = True


	def before_update_after_submit(self) :
		self.flags.ignore_links = True	



   		


	def before_submit(self) :
		self.flags.ignore_links = True
		if len(self.duty_and_taxes_template) < 1 :
			frappe.throw("There is no Duty and Taxes Template.")

		result = self.get_dtt()
		count = 0

		self.set('duty_and_taxes_template', [])

		if result :
			for i in range(len(result)) :
				if result[i][2] == 1 and result[i][3] == 0 :
					row = {
						"duty_and_taxes_template": result[i][0],
						"tracking_number": result[i][1],
						"shipment_number" : result[i][4],
					}
					self.append('duty_and_taxes_template', row)
					count = count + 1

		self.number_of_dtt_fetched = count		

		si_count = 0
		for row in self.duty_and_taxes_template :
			dtt_doc = frappe.get_doc("Duty and Taxes Template",row.duty_and_taxes_template)
			if dtt_doc.invoiced == 1 :
				row.logs = "Invoice already created before."
				continue
			elif dtt_doc.docstatus != 1 :
				row.logs = "This is Cancelled record."
				continue

			r2_list = frappe.db.get_list("R200000",
						filters={
							'shipment_number' : row.shipment_number ,
						},
						fields = ["billing_term_field"],
					 )
			
			if not r2_list :
				row.logs = "No respected record found in R200000."
				continue


			dtt_settings_doc = frappe.get_doc("Duty and Taxes Sales Invoice Settings")

			if r2_list[0].billing_term_field not in [dtt_settings_doc.billing_term_for_cod_service_provider, dtt_settings_doc.billing_term_for_ups_shipment, dtt_settings_doc.billing_term_for_corporate_customer ] :
				row.logs = "Billing Term is other than that are defined on 'Duty and Taxes Sales Invoice Settings' page."
				continue

			billing_term = r2_list[0].billing_term_field
			customer = None
			if billing_term == dtt_settings_doc.billing_term_for_cod_service_provider :
				customer = dtt_settings_doc.cod_service_provider_customer

			elif billing_term == dtt_settings_doc.billing_term_for_ups_shipment :
				customer = dtt_settings_doc.ups_shipment_customer
			
			elif billing_term == dtt_settings_doc.billing_term_for_corporate_customer :
				r4_list = frappe.db.get_list("R400000",
							filters={
								'shipment_number' : row.shipment_number ,
							},
							fields = ["name","consignee_number"],
				          )
				if not r4_list :
					row.logs = "No respected record found in R400000 for Corporate Customer."
					continue

				consignee_number = r4_list[0].consignee_number
				if not consignee_number :
					customer = dtt_settings_doc.unassign_customer
					# row.logs = "Consignee Number not found in R400000 for Corporate Customer."
					# continue


				else :
					icr_list = frappe.db.get_list("ICRIS List",
									filters={
										'shipper_no' : consignee_number ,
									},
									fields = ["shipper_name"],
								)

					if not icr_list :
						customer = dtt_settings_doc.unassign_customer
						# row.logs = "No respected record in ICRIS List found for Corporate Customer."
						# continue

					else :
						customer = icr_list[0].shipper_name

			if customer == None :
				row.logs = "No customer found."
				continue
			

			itm_sig = 0
			if dtt_settings_doc.duty_and_taxes_item :
				itm_sig = 1

				si_doc = frappe.new_doc("Sales Invoice")
				si_doc.customer = customer
				si_doc.posting_date = frappe.utils.today()
				si_doc.due_date = frappe.utils.today()
				si_doc.custom_duty_and_taxes_sales_invoice_uploader = self.name
				si_doc.custom_duty_and_taxes_template = dtt_doc.name
				si_doc.custom_billing_term = billing_term
				si_doc.custom_shipment_number = dtt_doc.shipment_number
				si_doc.custom_tracking_number = dtt_doc.tracking_number

				for x in dtt_settings_doc.duty_and_taxes_item :
					rate_value = getattr(dtt_doc, x.field_name, 0) 
					y = {'item_code': x.item, 'qty': 1 , 'rate': rate_value }
					si_doc.append('items',y)


			if dtt_settings_doc.clearance_type_items :
				itm_sig = 1
				for z in dtt_settings_doc.clearance_type_items :
					if z.clearance_type == dtt_doc.clearance_type and z.billing_term == billing_term :
						y1 = {'item_code': z.item, 'qty': 1 , 'rate': z.amount }
						si_doc.append('items',y1)


			if itm_sig == 1 :
				si_doc.insert()
				row.logs = "Invoice Created."
				frappe.db.set_value("Duty and Taxes Template", dtt_doc.name , "invoiced" , 1)
				si_count = si_count + 1
				


			else :
				row.logs = "No Item found from 'Duty and Tax Sales Invoice Settings' page that is why Item table of Sales Invoice is not creating."

		self.number_of_sales_invoice_created = si_count







				






