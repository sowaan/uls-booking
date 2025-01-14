# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document





class ShipmentMasterDetails(Document):
    
	def before_save(self) :
		get_records(self)

	@frappe.whitelist()
	def get_records_api(self):
		get_records(self)


def get_records(doc):
	doc = frappe.get_doc(doc)

	if not doc.master_package_id:
		return

	r6 = frappe.get_list('R600000', filters={
		'expanded_package_tracking_number': doc.master_package_id
	}, fields=['shipment_number', 'shipment_tracking_status', 'dws_actual_weight', 'dws_dim','time_of_dws','date_of_dws'])

	shipment_number = None  

	if r6:
		r6_record = r6[0]
		shipment_number = r6_record.get('shipment_number')
	else:
		shipment_number = frappe.db.get_value('R202000', {'custom_package_tracking_number': doc.master_package_id}, 'shipment_number')
		if shipment_number:
			frappe.msgprint('Shipment Number comes from R202000.')

	if not shipment_number:
		clear_form_fields(doc)
		frappe.msgprint("Master Package ID does not exist in the system.")
		return

	doc.shipment_number = shipment_number
	if r6:
		doc.shipment_tracking_status = r6_record.get('shipment_tracking_status', '')
		doc.dws_actual_ = r6_record.get('dws_actual_weight', '')
		doc.dws_dim_ = r6_record.get('dws_dim', '')
		doc.dws_time = r6_record.get('time_of_dws', '')
		doc.dws_date = r6_record.get('date_of_dws', '')

	populate_r202000_data(shipment_number, doc)
	populate_r200000_data(shipment_number, doc)
	populate_r201000_data(shipment_number, doc)
	populate_r300000_data(shipment_number, doc)
	populate_r400000_data(shipment_number, doc)
	populate_r500000_data(shipment_number, doc)
	populate_icris_data(doc)


def clear_form_fields(doc):
	fields_to_clear = [
		'shipment_number', 'origin_country', 'date_shipped', 'shipment_type', 'origin_port', 'destination_port',
		'shipment_tracking_status', 'bill_term_surcharge_indicator', 'split_duty_and_vat_flag','dws_date',
		'split_duty_and_vat_flag_master', 'billable_weight_', 'shipment_weight_', 'destination_country',
		'import_date', 'billing_term', 'dws_actual_', 'dws_dim_', 'shipment_weight_unit','declared_value',
		'number_of_packages_in_shipment', 'reference_number_1', 'reference_number_3', 'shipper_number',
		'shipper_contact_name', 'shipper_street', 'shipper_country', 'consignee_phone_number','dws_time',
		'shipper_postal_code', 'shipper_name', 'shipper_building', 'shipper_city', 'reference_number_2',
		'container_type_code', 'consignee_number', 'consignee_contact_name', 'consignee_street','currency_code_for_invoice_total',
		'consignee_country', 'shipper_phone_number', 'consignee_name', 'consignee_building', 'consignee_city',
		'consignee_postal_code', 'rating_pkg_2_type_code', 'invoice_description', 'invoice_value','customer_shipper','customer_consignee',
		'shipper_email_address', 'consignee_email_address', 'shipment_billing_type','currency_code_of_insured_amount'
	]
	
	for field in fields_to_clear:
		setattr(doc, field, None)  

	doc.dispute_invoice_number = []
	doc.dispute_invoice_number_billing = []
		

def populate_r202000_data(shipment_number, doc):
	r22 = frappe.get_list('R202000', filters={'shipment_number': shipment_number},
						fields=['custom_rating_pkg_2_type_code', 'custom_container_type_code'])
	if r22:
		r22_record = r22[0]
		doc.container_type_code = r22_record.get('custom_container_type_code', '')
		doc.rating_pkg_2_type_code = r22_record.get('custom_rating_pkg_2_type_code', '')
	else:
		doc.container_type_code = ''
		doc.rating_pkg_2_type_code = ''
		frappe.msgprint(f"No R202000 record on this Shipment number: {shipment_number}")


def populate_r200000_data(shipment_number, doc):
	r2 = frappe.get_list('R200000', filters={'shipment_number': shipment_number}, fields=[
		'origin_country', 'shipment_type', 'shipped_date', 'bill_term_surcharge_indicator','currency_code_for_invoice_total',
		'split_duty_and_vat_flag', 'shipment_weight', 'destination_country', 'import_date',
		'destination_port', 'billing_term_field', 'shipment_weight_unit','expanded_invoice_total',
		'number_of_packages_in_shipment', 'biling_type_shipment', 'origin_port','declared_value','currency_code_of_insured_amount'
	])

	if r2:
		record = r2[0]
		doc.origin_country = record.get('origin_country', '')
		doc.invoice_value = record.get('expanded_invoice_total', '')
		doc.date_shipped = record.get('shipped_date', '')
		doc.shipment_type = record.get('shipment_type', '')
		doc.bill_term_surcharge_indicator = record.get('bill_term_surcharge_indicator', '')
		doc.split_duty_and_vat_flag = record.get('split_duty_and_vat_flag', '')
		doc.shipment_weight_ = record.get('shipment_weight', '')
		doc.destination_country = record.get('destination_country', '')
		doc.import_date = record.get('import_date', '')
		doc.billing_term = record.get('billing_term_field', '')
		doc.shipment_weight_unit = record.get('shipment_weight_unit', '')
		doc.number_of_packages_in_shipment = record.get('number_of_packages_in_shipment', '')
		doc.shipment_billing_type = record.get('biling_type_shipment', '')
		doc.origin_port = record.get('origin_port', '')
		doc.destination_port = record.get('destination_port', '')
		doc.declared_value = record.get('declared_value', '')
		doc.currency_code_of_insured_amount = record.get('currency_code_of_insured_amount', '')
		doc.currency_code_for_invoice_total = record.get('currency_code_for_invoice_total', '')
	else:
		frappe.msgprint(f"No R200000 record on this tracking number: {doc.master_package_id}")


def populate_r201000_data(shipment_number, doc):
	r21 = frappe.get_value('R201000', {'shipment_number': shipment_number}, 'custom_minimum_bill_weight')
	doc.billable_weight_ = r21 or ''


def populate_r300000_data(shipment_number, doc):
	r3 = frappe.get_list('R300000', filters={'shipment_number': shipment_number}, fields=[
		'shipper_number', 'shipper_contact_name', 'shipper_street', 'shipper_country', 'shipper_postal_code',
		'shipper_name', 'shipper_building', 'shipper_city', 'shipper_phone_number', 'alternate_tracking_number_1'
	])
	if r3:
		shipper = r3[0]
		doc.shipper_number = shipper.get('shipper_number', '')
		doc.shipper_contact_name = shipper.get('shipper_contact_name', '')
		doc.shipper_street = shipper.get('shipper_street', '')
		doc.shipper_country = shipper.get('shipper_country', '')
		doc.shipper_postal_code = shipper.get('shipper_postal_code', '')
		doc.shipper_name = shipper.get('shipper_name', '')
		doc.shipper_building = shipper.get('shipper_building', '')
		doc.shipper_city = shipper.get('shipper_city', '')
		doc.shipper_phone_number = shipper.get('shipper_phone_number', '')
		doc.reference_number_1 = shipper.get('alternate_tracking_number_1', '')
		shipper_number = shipper.get('shipper_number')
		cus_shipper_name = None
		if shipper_number:
			icris_shipper_name = frappe.get_value('ICRIS List', {'shipper_no': shipper_number}, 'shipper_name')
			
			if icris_shipper_name:
				cus_shipper_name = icris_shipper_name
			else:
				customer_shipper_name = frappe.get_value('Customer', {'custom_import_account_no': shipper_number}, 'customer_name')
				if customer_shipper_name:
					cus_shipper_name = customer_shipper_name
					# doc.shipper_name = customer_shipper_name

		if cus_shipper_name:
			if doc.origin_country and doc.origin_country.upper() in ['PK', 'PAK', 'PAKISTAN']:
					doc.customer_shipper = cus_shipper_name


def populate_r400000_data(shipment_number, doc):
	r4 = frappe.get_list('R400000', filters={'shipment_number': shipment_number}, fields=[
		'consignee_number', 'consignee_contact_name', 'consignee_street', 'alternate_tracking_number_2',
		'consignee_country_code', 'consignee_name', 'consignee_building', 'consignee_po_number',
		'consignee_city', 'consignee_postal_code', 'consignee_phone_number'
	])
	if r4:
		consignee = r4[0]
		doc.consignee_number = consignee.get('consignee_number', '')
		doc.consignee_contact_name = consignee.get('consignee_contact_name', '')
		doc.consignee_street = consignee.get('consignee_street', '')
		doc.consignee_country = consignee.get('consignee_country_code', '')
		doc.consignee_name = consignee.get('consignee_name', '')
		doc.consignee_building = consignee.get('consignee_building', '')
		doc.consignee_city = consignee.get('consignee_city', '')
		doc.consignee_postal_code = consignee.get('consignee_postal_code', '')
		doc.consignee_phone_number = consignee.get('consignee_phone_number', '')
		doc.reference_number_2 = consignee.get('alternate_tracking_number_2', '')
		doc.reference_number_3 = consignee.get('consignee_po_number', '')
		consignee_number = consignee.get('consignee_number')
		cus_consignee_name = None
		if consignee_number:
			icris_consignee_name = frappe.get_value('ICRIS List', {'shipper_no': consignee_number}, 'shipper_name')
			if icris_consignee_name:
				cus_consignee_name = icris_consignee_name
			else:
				customer_consignee_name = frappe.get_value('Customer', {'custom_import_account_no': consignee_number}, 'customer_name')
				if customer_consignee_name:
					cus_consignee_name = customer_consignee_name
					# doc.consignee_name = customer_consignee_name
		if cus_consignee_name:
			if doc.origin_country and doc.origin_country.upper() not in ['PK', 'PAK', 'PAKISTAN']:
				doc.customer_consignee = cus_consignee_name

			
def populate_r500000_data(shipment_number, doc):
    result = frappe.db.get_value(
        'R500000', 
        {'shipment_number': shipment_number}, 
        'custom_invdesc'
    )

    if result:
        doc.invoice_description = result


def populate_icris_data(doc):
	if doc.customer_consignee and doc.customer_consignee.strip():
		result = frappe.db.get_value("Sales Invoice", {"customer": doc.customer_consignee, "custom_shipment_number": doc.shipment_number}, "name", order_by="creation desc")
		if result:
			doc.append('dispute_invoice_number',{
				'customers_sales_invoice': result
			})
			doc.append('dispute_invoice_number_billing',{
				'customers_sales_invoice': result
			})
	elif doc.customer_shipper and doc.customer_shipper.strip():
		result = frappe.db.get_value("Sales Invoice", {"customer": doc.customer_shipper, "custom_shipment_number": doc.shipment_number}, "name", order_by="creation desc")
		if result:
			doc.append('dispute_invoice_number',{
				'customers_sales_invoice': result
			})
			doc.append('dispute_invoice_number_billing',{
				'customers_sales_invoice': result
			})
	else:
		return







	# origin_country = doc.origin_country
	# shipper_number = doc.shipper_number
	# consignee_number = doc.consignee_number

	# if origin_country.upper() in ['PK', 'PAK', 'PAKISTAN']:
	# 	icris_shipper = frappe.get_value('ICRIS List', {'shipper_no': shipper_number}, 'shipper_name')
	# 	if icris_shipper:
	# 		email_id_shipper = frappe.get_value('Customer', {'customer_name': icris_shipper}, 'email_id')
	# 		if email_id_shipper:
	# 			doc.shipper_email_address = email_id_shipper
	# 	else:
	# 		frappe.msgprint(f"There is no shipper of this shipper number in Icris List.")
	# else:
	# 	icris_consignee = frappe.get_value('ICRIS List', {'shipper_no': consignee_number}, 'shipper_name')
	# 	if icris_consignee:
	# 		email_id_consignee = frappe.get_value('Customer', {'customer_name': icris_consignee}, 'email_id')
	# 		if email_id_consignee:
	# 			doc.consignee_email_address = email_id_consignee
	# 	else:
	# 		frappe.msgprint(f"There is no consignee of this consignee number in Icris List.")







