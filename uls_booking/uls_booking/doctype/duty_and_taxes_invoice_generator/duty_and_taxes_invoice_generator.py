# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
import json

class DutyandTaxesInvoiceGenerator(Document):
	# pass



	@frappe.whitelist()	
	def get_dtt(self) :
		result = frappe.db.sql(
            """
            select name, tracking_number, docstatus, invoiced, shipment_number, vendor from `tabDuty and Taxes Template`
            where ( mawb_number LIKE %(mawb_number)s )
            """,
            {"mawb_number": self.mawb_number},
        )
		return result
		


	def before_save(self) :

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
						'docstatus' : 1 ,
					}
					self.append('duty_and_taxes_template', row)
					count = count + 1
		self.number_of_dtt_fetched = count


		


	def validate(self) :
		self.flags.ignore_links = True


	def before_update_after_submit(self) :
		self.flags.ignore_links = True	



   		


@frappe.whitelist()
def create_sales_invoices(rec_name) :
	self = frappe.get_doc("Duty and Taxes Invoice Generator", rec_name)
	# self.flags.ignore_links = True
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

	frappe.db.set_value(self.doctype , self.name , "number_of_dtt_fetched" , count)		

	si_count = 0
	for row in self.duty_and_taxes_template :
		values = {
			'dt_inv_gen' : self.name ,
			'shipment_numb' : row.shipment_number
		}

		# frappe.msgprint(str(row))

		dtt_doc = frappe.get_doc("Duty and Taxes Template",row.duty_and_taxes_template)

		if dtt_doc.invoiced == 1 :
			# frappe.msgprint( str("Duty and Taxes Template Records Table") + "  " +str(row.name))
			# frappe.db.set_value( "Duty and Taxes Template Records Table" , row.name , "logs" , "Invoice already created before." )
			query = """
				UPDATE `tabDuty and Taxes Template Records Table`
				SET logs = 'Invoice already created before.'
				WHERE parent = %(dt_inv_gen)s and shipment_number = %(shipment_numb)s
			"""
			frappe.db.sql(query , values=values, as_dict=0)
			continue
		elif dtt_doc.docstatus != 1 :
			# frappe.msgprint( str("Duty and Taxes Template Records Table") + "  " +str(row.name))
			# frappe.db.set_value( "Duty and Taxes Template Records Table" , row.name , "logs" , "This is Cancelled record." )
			query = """
				UPDATE `tabDuty and Taxes Template Records Table`
				SET logs = 'This is Cancelled record.'
				WHERE parent = %(dt_inv_gen)s and shipment_number = %(shipment_numb)s
			"""
			frappe.db.sql(query , values=values, as_dict=0)
			continue

		r2_list = frappe.db.get_list("R200000",
					filters={
						'shipment_number' : row.shipment_number ,
					},
					fields = ["billing_term_field","shipment_type","shipment_weight","custom_shipment_weight_unit","currency_code_for_invoice_total","expanded_invoice_total","shipped_date","input_date","number_of_packages_in_shipment"],
					)
		

		r4_list = frappe.db.get_list("R400000",
						filters={
							'shipment_number' : row.shipment_number ,
						},
						fields = ["name","consignee_number","consignee_contact_name","consignee_building","consignee_street","consignee_city","consignee_phone_number","consignee_number","consignee_postal_code","consignee_country_code","consignee_name"],
						)

		r3_list = frappe.db.get_list("R300000",
						filters={
							'shipment_number' : row.shipment_number ,
						},
						fields = ["name","shipper_name","shipper_contact_name","shipper_country","shipper_city","shipper_postal_code","shipper_phone_number","shipper_number"],
						)			   
		
		


		dtt_settings_doc = frappe.get_doc("Duty and Taxes Sales Invoice Settings")

		
		billing_term = None
		customer = None
		attn_name = None
		consignee_building = None
		consignee_street = None
		consignee_city = None
		consignee_phone = None
		unassign_cust_flag = 0

		if r2_list :
			billing_term = r2_list[0].billing_term_field

		



		if dtt_doc.customer :
			customer = dtt_doc.customer

		elif dtt_doc.unassing_customer == 1 :
			customer = dtt_settings_doc.unassign_customer
			unassign_cust_flag = 1
		
		else :
			loc = dtt_doc.location
			cust_found_flag = 0
			if r2_list :
				billing_term = r2_list[0].billing_term_field
			if r4_list :
				consignee_city = r4_list[0].consignee_city

			for row1 in dtt_settings_doc.unassigned_cod_dt_customer :
				if row1.location == loc and row1.billing_term == billing_term and row1.consignee_city == consignee_city :
					customer = row1.customer
					cust_found_flag = 1
					break
			if cust_found_flag == 0 :
				customer = dtt_settings_doc.unassign_customer
				unassign_cust_flag = 1


		if r4_list :
			attn_name = r4_list[0].consignee_contact_name
			consignee_building = r4_list[0].consignee_building
			consignee_street = r4_list[0].consignee_street
			consignee_city = r4_list[0].consignee_city
			consignee_phone = r4_list[0].consignee_phone_number
		

		itm_sig = 0
		si_doc = frappe.new_doc("Sales Invoice")
		si_doc.customer = customer
		si_doc.posting_date = frappe.utils.today()
		si_doc.due_date = frappe.utils.today()
		si_doc.custom_duty_and_taxes_invoice_generator = self.name
		si_doc.custom_duty_and_taxes_template = dtt_doc.name
		si_doc.custom_billing_term = billing_term
		si_doc.custom_shipment_number = dtt_doc.shipment_number
		si_doc.custom_tracking_number = dtt_doc.tracking_number
		si_doc.custom_consignee_contact_name = attn_name
		si_doc.custom_consignee_building = consignee_building
		si_doc.custom_consignee_street = consignee_street
		si_doc.custom_consignee_city = consignee_city
		si_doc.custom_consignee_phone_number = consignee_phone
		si_doc.custom_duty_and_taxes_invoice = 1
		si_doc.custom_mawb_number = dtt_doc.mawb_number
		si_doc.custom_dt_vendor = dtt_doc.vendor
		si_doc.custom_arrival_date = dtt_doc.arrival_date
		si_doc.custom_type = dtt_doc.type
		si_doc.custom_location = dtt_doc.location
		si_doc.custom_clearance_type = dtt_doc.clearance_type


		if r4_list :
			if frappe.db.exists("ICRIS Account", r4_list[0].consignee_number):
				si_doc.custom_consignee_number = r4_list[0].consignee_number
			si_doc.custom_consignee_postal_code = r4_list[0].consignee_postal_code
			si_doc.custom_consignee_country = r4_list[0].consignee_country_code
			si_doc.custom_consignee_name = r4_list[0].consignee_name
		

		if r3_list :
			si_doc.custom_shipper_name = r3_list[0].shipper_name
			si_doc.custom_shipper_contact_name = r3_list[0].shipper_contact_name
			si_doc.custom_shipper_country = r3_list[0].shipper_country
			si_doc.custom_shipper_city = r3_list[0].shipper_city
			si_doc.custom_shipper_postal_code = r3_list[0].shipper_postal_code
			si_doc.custom_shipper_phone_number = r3_list[0].shipper_phone_number
			if frappe.db.exists("ICRIS Account", r3_list[0].shipper_number):
				si_doc.custom_shipper_number = r3_list[0].shipper_number


		if r2_list :
			si_doc.custom_shipment_type_dt = r2_list[0].shipment_type
			si_doc.custom_shipment_weight = r2_list[0].shipment_weight
			si_doc.custom_shipment_weight_unit = r2_list[0].custom_shipment_weight_unit
			si_doc.custom_currency_code_for_invoice_total = r2_list[0].currency_code_for_invoice_total
			si_doc.custom_expanded_invoice_total = r2_list[0].expanded_invoice_total
			si_doc.custom_date_shipped = r2_list[0].shipped_date
			si_doc.custom_booking_date = r2_list[0].input_date
			si_doc.custom_packages = r2_list[0].number_of_packages_in_shipment



		if dtt_settings_doc.duty_and_taxes_item :
			itm_sig = 1

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
			if self.submit_invoices == 1 and unassign_cust_flag == 0 :
				si_doc.submit()
				
			if unassign_cust_flag == 0 :
				# frappe.msgprint( str("Duty and Taxes Template Records Table") + "  " +str(row.name))
				# frappe.db.set_value("Duty and Taxes Template Records Table" , row.name , "logs" , "Invoice Created.")
				query = """
				UPDATE `tabDuty and Taxes Template Records Table`
				SET logs = 'Invoice Created.'
				WHERE parent = %(dt_inv_gen)s and shipment_number = %(shipment_numb)s
				"""
				frappe.db.sql(query , values=values, as_dict=0)
			
			elif unassign_cust_flag == 1 :
				# frappe.msgprint( str("Duty and Taxes Template Records Table") + "  " +str(row.name))
				# frappe.db.set_value("Duty and Taxes Template Records Table" , row.name , "logs" , "Invoice Created with Unassign Customer.")
				query = """
				UPDATE `tabDuty and Taxes Template Records Table`
				SET logs = 'Invoice Created with Unassign Customer.'
				WHERE parent = %(dt_inv_gen)s and shipment_number = %(shipment_numb)s
				"""
				frappe.db.sql(query , values=values, as_dict=0)
			frappe.db.set_value("Duty and Taxes Template", dtt_doc.name , "invoiced" , 1)
			si_count = si_count + 1
			


		else :
			# frappe.msgprint( str("Duty and Taxes Template Records Table") + "  " +str(row.name))
			# frappe.db.set_value( "Duty and Taxes Template Records Table" , row.name , "logs" , "No Item found from 'Duty and Tax Sales Invoice Settings' page that is why Item table of Sales Invoice is not creating.")
			query = """
				UPDATE `tabDuty and Taxes Template Records Table`
				SET logs = 'No Item found from 'Duty and Tax Sales Invoice Settings' page that is why Item table of Sales Invoice is not creating.'
				WHERE parent = %(dt_inv_gen)s and shipment_number = %(shipment_numb)s
			"""
			frappe.db.sql(query , values=values, as_dict=0)

	frappe.db.set_value(self.doctype , self.name , "number_of_sales_invoice_created" , si_count)
	frappe.db.set_value(self.doctype , self.name , "all_sales_invoice_created" , 1)

	return True

@frappe.whitelist()
def create_purchase_invoice(rec_name):
	self = frappe.get_doc("Duty and Taxes Invoice Generator", rec_name)
	supplier_record = frappe.get_list(
    "Duty and Taxes Template",
    filters={'mawb_number': self.mawb_number},
    fields=["vendor", "flight_number", "arrival_date","mno"]
		)
	if supplier_record[0].vendor :

		dtt_settings_doc = frappe.get_doc("Duty and Taxes Sales Invoice Settings")
		if frappe.db.exists("Purchase Invoice", {"mawb_number": self.mawb_number}):
			frappe.db.set_value("Duty and Taxes Invoice Generator",self.name,"log","Purchase invoice already created before.")
		else:
			
			pi_doc = frappe.new_doc("Purchase Invoice")
			pi_doc.posting_date = frappe.utils.today()
			pi_doc.supplier = supplier_record[0].vendor
			pi_doc.custom_mawb_number = self.mawb_number
			pi_doc.custom_flight_number = supplier_record[0].flight_number
			pi_doc.custom_arrival_date = supplier_record[0].arrival_date
			pi_doc.custom_mno = supplier_record[0].mno
			pi_row1 = {'item_code': dtt_settings_doc.purchase_invoice_item , 'qty': 1 , 'rate': self.purchase_invoice_amount }
			pi_doc.items = []
			pi_doc.append('items',pi_row1)
			pi_doc.custom_duty_and_taxes_invoice = 1
			pi_doc.insert()
			
			frappe.db.set_value("Duty and Taxes Invoice Generator",self.name,"purchase_invoice_created",1)
	else :
		frappe.db.set_value("Duty and Taxes Invoice Generator",self.name,"log","Supplier Not Found")












