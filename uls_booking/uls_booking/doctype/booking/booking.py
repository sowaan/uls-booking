# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import requests
from PIL import Image
from frappe.utils.pdf import get_pdf
import io
import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import nowdate
from uls_booking.uls_booking.api.api import (generate_token, create_shipment ,cancel_shipment, label_recovery, tracking)
import base64
from frappe.utils.file_manager import save_file


class Booking(WebsiteGenerator):


	def before_submit(self) :
		if self.customer and self.company :
			credit_limit_used = 0.00
			total_credit_limit = 0.00
			booking_list = frappe.get_list('Booking',
								filters = {
									'customer': self.customer,
									'company': self.company,
									'docstatus': 1
								},
								fields = ['name', 'amount_after_discount']
							)
			if booking_list :
				for booking in booking_list :
					credit_limit_used = credit_limit_used + booking.amount_after_discount
			
			cust_doc = frappe.get_doc('Customer',self.customer)
				
			if cust_doc.credit_limits :
				for row in cust_doc.credit_limits :
					if row.company == self.company :
						total_credit_limit = row.credit_limit 
						break

			balance_before_ship = total_credit_limit - credit_limit_used
			if balance_before_ship <= 0 :
				frappe.throw("Customer's Balance Credit Limit is zero." )
			else : 
				self.balance_credit_limit_before_shipment = balance_before_ship

		if self.amount_after_discount > self.balance_credit_limit_before_shipment :
			frappe.throw("Your credit limit is not enough to make this shipment")
		else :
			self.balance_credit_limit_after_shipment = self.balance_credit_limit_before_shipment - self.amount_after_discount


		token = generate_token()
		data = create_shipment(token , self.name)


		if data['ShipmentResponse']['ShipmentResults']['ShipmentIdentificationNumber'] :
			shipment_identification_number = data['ShipmentResponse']['ShipmentResults']['ShipmentIdentificationNumber']
			self.shipment_identification_number = shipment_identification_number

			if 'PackageResults' in data['ShipmentResponse']['ShipmentResults']:
				package_results = data['ShipmentResponse']['ShipmentResults']['PackageResults']

			if isinstance(package_results, dict):
				package_results = [package_results]

			
			# for package in package_results :
			# 	tracking_number = package.get('TrackingNumber')
			# 	shipping_label = package.get('ShippingLabel', {})
			# 	graphic_image = shipping_label.get('GraphicImage')

			# 	if tracking_number and graphic_image :
			# 		image_data = base64.b64decode(graphic_image)
			# 		image = Image.open(io.BytesIO(image_data))

			# 		image_rgb = image.convert('RGB')
			# 		temp_image_path = f"/tmp/{tracking_number}_label.jpg"
			# 		image_rgb.save(temp_image_path)


			# 		html_content = f"""
			# 			<html>
			# 				<body>
			# 					<img src="{temp_image_path}" width="500"/>
			# 				</body>
			# 			</html>
			# 		"""

			# 		pdf_data = get_pdf(html_content)

			# 		file_name = f"{tracking_number}_label.pdf"
			# 		file_url = save_file(file_name, pdf_data, self.doctype, self.name, is_private=0)

			# 		self.append('tracking_numbers_and_images', {
			# 			'tracking_number': tracking_number,
			# 			'label': file_url.file_url
			# 		})



			self.set('tracking_numbers_and_images', [])
			
			for package in package_results:
				tracking_number = package.get('TrackingNumber')
				shipping_label = package.get('ShippingLabel', {})
				graphic_image = shipping_label.get('GraphicImage')

				if tracking_number and graphic_image:
					image_data = base64.b64decode(graphic_image)
					file_name = f"{tracking_number}_label.gif"
					file_url = save_file(file_name, image_data, self.doctype, self.name, is_private=0)

					self.append('tracking_numbers_and_images', {
						'tracking_number': tracking_number ,
						'label' : file_url.file_url
					})

		self.document_status = 'Submitted'		



	def on_submit(self) :				

		token = generate_token()
		data = tracking(token , self.shipment_identification_number)

		try :
			frappe.db.set_value( "Booking" , self.name , "current_status" , data['trackResponse']['shipment'][0]['package'][0]['currentStatus']['description'])
			frappe.db.set_value( "Booking" , self.name , "current_status_code" , data['trackResponse']['shipment'][0]['package'][0]['currentStatus']['code'])

			# self.current_status = data['trackResponse']['shipment'][0]['package'][0]['currentStatus']['description']
			# self.current_status_code = data['trackResponse']['shipment'][0]['package'][0]['currentStatus']['code']

			# self.set("current_status", data['trackResponse']['shipment'][0]['package'][0]['currentStatus']['description'])
			# self.set("current_status_code", data['trackResponse']['shipment'][0]['package'][0]['currentStatus']['code'])

		except KeyError as e:

			frappe.throw(f"Failed to retrieve shipment status information: {str(e)}")



	def before_cancel(self) :

		if self.shipment_identification_number :
			token = generate_token()
			cancel_shipment(token , self.name)
			# frappe.throw(str(token))
		self.document_status = 'Cancelled'



	def before_save(self):


		flg = 0
		icris_doc = frappe.get_doc("ICRIS Account", self.icris_account)
		if icris_doc.rate_group :
			for row in icris_doc.rate_group:
				if row.service_type == self.service_type and str(self.posting_date) >= str(row.from_date) and str(self.posting_date) <= str(row.to_date) :
					rate_grp = row.rate_group
					flg = 1
					break

		if flg == 0:
			frappe.throw("The rate list for the given service type is not attached to the given ICRIS Account.")
	





		self.extended_area_surcharge = 0
		self.remote_area_surcharge = 0
		self.add_handling_charges = 0
		self.lps = 0



		weight_temp = 0.0
		declare_temp = 0.0
		pdl = frappe.get_doc('Package Dimensions Limitation','Package Dimensions Limitation')



		for row in self.parcel_information :

			if not row.length :
				row.length = 1
			if not row.width :
				row.width = 1
			if not row.height :
				row.height = 1

			numbers = [row.length , row.width , row.height ]
			numbers.sort(reverse=True)
			row.length = float(numbers[0])	
			row.width = float(numbers[1])
			row.height = float(numbers[2])
			girth = 0

			
	

			if float(row.length) > float(pdl.max_length) :
				frappe.throw(f"Maximum length per package is {pdl.max_length} cm.")

			else :
				girth = (row.width*2) + (row.height*2)
				if float(float(girth) + float(row.length)) > float(pdl.max_girth) :
					frappe.throw("Maximum size per package should not be Greater than 400cm in Length and Girth[(2 x width) + (2 x height)] combined.")	



			row.total_weight = row.weight_per_parcel * row.total_identical_parcels
			row.dim_weight = row.length * row.width * row.height / 5000
			row.total_dim_weight =  ( row.length * row.width * row.height / 5000 ) * row.total_identical_parcels
			row.actual_weight_per_parcel = max( row.weight_per_parcel , row.dim_weight )
			row.actual_weight = max( row.total_weight , row.total_dim_weight )


			weight_temp = weight_temp + row.actual_weight
			if row.declare_value :
				declare_temp = declare_temp + int(row.declare_value)
		
		self.total_actual_weight = weight_temp
		self.weight = weight_temp
		self.total_declare_value = declare_temp



		if self.customer and self.company :
			credit_limit_used = 0.00
			total_credit_limit = 0.00
			booking_list = frappe.get_list('Booking',
								filters = {
									'customer': self.customer,
									'company': self.company,
									'docstatus': 1
								},
								fields = ['name', 'amount_after_discount']
							)
			if booking_list :
				for booking in booking_list :
					credit_limit_used = credit_limit_used + booking.amount_after_discount
			
			cust_doc = frappe.get_doc('Customer',self.customer)
				
			if cust_doc.credit_limits :
				for row in cust_doc.credit_limits :
					if row.company == self.company :
						total_credit_limit = row.credit_limit 
						break

			balance_before_ship = total_credit_limit - credit_limit_used
			if balance_before_ship <= 0 :
				frappe.throw("Customer's Balance Credit Limit is zero." )
			else : 
				self.balance_credit_limit_before_shipment = balance_before_ship

		
		total_add_ch = 0
		max_ovr_lmt = 0
		lps = 0
		add_handling = 0
		ex_area = 0
		rem_area = 0
		sat_del = 0

		if self.ic_label == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				total_add_ch = total_add_ch + add_charge_doc.import_control_amount_per_shipment
				self.ic_label = 1

		if self.return_electronic_label == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				total_add_ch = total_add_ch + add_charge_doc.return_electronic_amount_per_shipment

		if self.shipping_bill_charges == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				if self.imp__exp == 'Import' :
					self.sbc = add_charge_doc.import_amount_per_shipment
				elif self.imp__exp == 'Export' :
					self.sbc = add_charge_doc.export_amount_per_shipment  

		if self.duty_tax_forwarding == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				total_add_ch = total_add_ch + add_charge_doc.duty_and_tax_forwarding_amount_per_shipment

		if self.residential_surcharge == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				total_add_ch = total_add_ch + add_charge_doc.residential_surcharge_amount_per_shipment

		if self.saturday_delivery == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				total_add_ch = total_add_ch + add_charge_doc.saturday_delivery_amount_per_shipment
				sat_del = add_charge_doc.amount

		if self.direct_delivery == 1 :
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			if add_charge_doc :
				pkg_count = 0
				for x in self.parcel_information :
					pkg = frappe.get_doc('Package Types', x.packaging_type)
					if pkg.package == 1 :
						pkg_count = pkg_count + x.total_identical_parcels
				total_add_ch = total_add_ch + (add_charge_doc.direct_delivery_amount_per_package * pkg_count)

		if self.signature_options == 1 :
			if self.select_signature_option == 'Delivery Confirmation Signature' :
				add_charge_doc = frappe.get_doc('Additional Charges Page')
				if add_charge_doc :
					total_add_ch = total_add_ch + add_charge_doc.delivery_confimation_signature_amount_per_shipment
			
			else :
				add_charge_doc = frappe.get_doc('Additional Charges Page')
				if add_charge_doc :
					total_add_ch = total_add_ch + add_charge_doc.delivery_confimation_adult_signature_amount_per_shipment


		
		# Extended / Remote Area

		other_postal_code = None
		other_country = None
		if self.imp__exp == 'Import' :
			if self.is_customer1 == 1 :
				other_postal_code = self.shipper_postal_code
				other_country = self.shipper_country
			else :
				other_postal_code = self.consignee_postal_code
				other_country = self.consignee_country

		elif self.imp__exp == 'Export' :
			if self.is_customer == 1 :
				other_postal_code = self.shipper_postal_code
				other_country = self.shipper_country
			else :
				other_postal_code = self.postal_code
				other_country = self.country


		c_doc = frappe.get_doc("Customer",self.customer)
		pc_list = frappe.get_list('Postal Codes',
						   filters = {
							   'country' : other_country,
							   'postal_code' : other_postal_code , 
						   }, ignore_permissions = True
						   , fields=['name'])
						
		if pc_list :
			pc_doc = frappe.get_doc('Postal Codes',pc_list[0].name)
			# pc_doc = frappe.get_doc('Postal Codes',dest_postal_code)
			if pc_doc :
				if pc_doc.area == 'Extended' :
					if c_doc.custom_extended_area_surcharge == 1:
						self.extended_area_surcharge = 1
						add_charge_doc = frappe.get_doc('Additional Charges Page')
						amount_per_kg = float(add_charge_doc.extended_area_amount_per_kg)
						weight = float(self.weight)
						w = amount_per_kg * weight
						total_add_ch = total_add_ch + max(add_charge_doc.extended_area_amount_per_shipment, w)
						ex_area = ex_area + max(add_charge_doc.extended_area_amount_per_shipment, w)

				elif pc_doc.area == 'Remote' :
					if c_doc.custom_remote_area_surcharge == 1:
						self.remote_area_surcharge = 1
						add_charge_doc = frappe.get_doc('Additional Charges Page')
						amount_per_kg = float(add_charge_doc.remote_area_amount_per_kg)
						weight = float(self.weight)
						w = amount_per_kg * weight
						total_add_ch = total_add_ch + max(add_charge_doc.remote_area_amount_per_shipment, w)
						rem_area = rem_area + max(add_charge_doc.remote_area_amount_per_shipment, w)

		
		# Maximum Over Limit
		if c_doc.custom_over_maximum_limit == 1 :
			add_charge_type = 'Over Maximum Limits Fee'			
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			actual_weight = 0
			no_of_pkg_for_avg = 0
			single_pkg_no = 0
			single_pkg_no_for_dim = 0
			avg = 0

			for row in self.parcel_information:
				if row.packaging_type:
					pkg_doc = frappe.get_doc("Package Types", row.packaging_type)
				else:
					frappe.throw("Complete Package Details.")
					
				if pkg_doc.package == 1:
					no_of_pkg_for_avg += row.total_identical_parcels
					actual_weight += row.actual_weight
					if row.actual_weight_per_parcel > add_charge_doc.over_maximum_limit_max_weight:
						single_pkg_no += row.total_identical_parcels
						row.max_over_limit = 1
					elif ( (row.length + ((2 * row.width) + (2 * row.height))) > add_charge_doc.over_maximum_limit_max_length_plus_girth_in_cm ) or (row.length > add_charge_doc.over_maximum_limit_max_length_longest_side_in_cm) :
						single_pkg_no_for_dim += row.total_identical_parcels
						row.max_over_limit = 1

			if single_pkg_no > 0:
				total_add_ch = total_add_ch + max(single_pkg_no * add_charge_doc.over_maximum_limit_amount_per_package, add_charge_doc.over_maximum_limit_minimum_amount)
				self.maximum_over_limit = 1
				max_ovr_lmt = max_ovr_lmt + max(single_pkg_no * add_charge_doc.over_maximum_limit_amount_per_package, add_charge_doc.over_maximum_limit_minimum_amount)
			if single_pkg_no_for_dim > 0:
				total_add_ch = total_add_ch + max(single_pkg_no * add_charge_doc.over_maximum_limit_amount_per_package, add_charge_doc.over_maximum_limit_minimum_amount)
				self.maximum_over_limit = 1
				max_ovr_lmt = max_ovr_lmt + max(single_pkg_no * add_charge_doc.over_maximum_limit_amount_per_package, add_charge_doc.over_maximum_limit_minimum_amount)

		
		# LPS
		if c_doc.custom_large_package_surcharge == 1 :
			add_charge_type = 'Large Package Surcharge'
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			actual_weight = 0
			no_of_pkg_for_avg = 0
			single_pkg_no = 0
			single_pkg_no_for_dim = 0
			avg = 0
		
			for row in self.parcel_information:
				if row.max_over_limit != 1 :
					if row.packaging_type:
						pkg_doc = frappe.get_doc("Package Types", row.packaging_type)
					else:
						frappe.throw("Complete Package Details.")
						
					if pkg_doc.package == 1:
						no_of_pkg_for_avg += row.total_identical_parcels
						actual_weight += row.actual_weight
						if row.actual_weight_per_parcel > add_charge_doc.large_package_surcharge_max_weight:
							single_pkg_no += row.total_identical_parcels
							row.lps = 1
						elif (row.length + ((2 * row.width) + (2 * row.height))) > add_charge_doc.large_package_surcharge_max_length_plus_girth_in_cm:
							single_pkg_no_for_dim += row.total_identical_parcels
							row.lps = 1

			if single_pkg_no > 0:
				total_add_ch = total_add_ch + max(single_pkg_no * add_charge_doc.large_package_surcharge_amount, add_charge_doc.large_package_surcharge_minimum_amount)
				self.lps = 1
				lps = lps + max(single_pkg_no * add_charge_doc.large_package_surcharge_amount, add_charge_doc.large_package_surcharge_minimum_amount)
			if single_pkg_no_for_dim > 0:
				total_add_ch = total_add_ch + max(single_pkg_no * add_charge_doc.large_package_surcharge_amount, add_charge_doc.large_package_surcharge_minimum_amount)
				self.lps = 1
				lps = lps + max(single_pkg_no * add_charge_doc.large_package_surcharge_amount, add_charge_doc.large_package_surcharge_minimum_amount)



		
		# Add Handling	
		if c_doc.custom_additional_handling_charges == 1:
			add_charge_doc = frappe.get_doc('Additional Charges Page')
			actual_weight = 0
			no_of_pkg_for_avg = 0
			single_pkg_no = 0
			avg = 0
			for row in self.parcel_information :
				if row.max_over_limit != 1 and row.lps != 1 :
					pkg_doc = frappe.get_doc("Package Types",row.packaging_type)
					if pkg_doc.package == 1 :
						no_of_pkg_for_avg = no_of_pkg_for_avg + row.total_identical_parcels
						actual_weight = actual_weight + row.actual_weight
						if (row.actual_weight_per_parcel > add_charge_doc.add_handling_max_weight) or (row.length > add_charge_doc.add_handling_max_length_longest_side_in_cm) or (row.width > add_charge_doc.add_handling_max_width_second_longest_side_in_cm) or (row.height > add_charge_doc.add_handling_max_width_second_longest_side_in_cm) :
							single_pkg_no = single_pkg_no + row.total_identical_parcels
							row.add_handling = 1

			if no_of_pkg_for_avg > 0 :
				avg = actual_weight / no_of_pkg_for_avg         

			if avg > add_charge_doc.add_handling_max_weight :
				total_add_ch = total_add_ch +  max(no_of_pkg_for_avg*add_charge_doc.add_handling_amount_per_package , add_charge_doc.add_handling_minimum_amount )
				add_handling = add_handling + max(no_of_pkg_for_avg*add_charge_doc.add_handling_amount_per_package , add_charge_doc.add_handling_minimum_amount )
				self.add_handling_charges = 1

			else :
					if single_pkg_no > 0 :
						total_add_ch = total_add_ch +  max(single_pkg_no*add_charge_doc.add_handling_amount_per_package , add_charge_doc.add_handling_minimum_amount )
						add_handling = add_handling + max(no_of_pkg_for_avg*add_charge_doc.add_handling_amount_per_package , add_charge_doc.add_handling_minimum_amount )
						self.add_handling_charges = 1


			
			
			self.total_additional_charges = total_add_ch


		#Insurance On Declare Value
		if c_doc.custom_insurance_of_declared_value == 1:
			if self.total_declare_value > 0 :
				dec_doc = frappe.get_doc('Additional Charges Page')
				self.insurance = max((self.total_declare_value * dec_doc.percentage_on_declare_value / 100) , dec_doc.minimum_amount_for_declare_value)


		# Zone
		if self.imp__exp == 'Export':
			country = frappe.get_list('Country Names',
								filters = {
									'countries': other_country,
								},
								fields = ['parent'],
								ignore_permissions=True)
			self.zone = country[0].parent if country else None
		else:
			country = frappe.get_list('Country Names',
								filters = {
									'countries': other_country,
								},
								fields = ['parent'],
								ignore_permissions=True)
			self.zone = country[0].parent if country else None

		
		# Calculate Rate
		if self.zone and self.weight:
			amount = 0.0
			env_weight = 0.0
			doc_weight = 0.0
			pack_weight = 0.0
			count = 0
			pack_types = set()
			packaging_type_weights = {}
			last_row_rate = {}
			today = nowdate()

			for row in self.parcel_information:
				rate_list = frappe.get_list("Selling Rate", filters={
					'country': other_country,
					'based_on': 'Country',
					'import__export': self.imp__exp,
					'mode_of_transportation': self.mode_of_transportation,
					'service_type': self.service_type,
					'package_type': row.packaging_type,
					'rate_group': rate_grp,
				})

				if not rate_list:
					rate_list = frappe.get_list("Selling Rate", filters={
						'zone': self.zone,
						'based_on': 'Zone',
						'import__export': self.imp__exp,
						'mode_of_transportation': self.mode_of_transportation,
						'service_type': self.service_type,
						'package_type': row.packaging_type,
						'rate_group': rate_grp,
					})

				if rate_list:
					rate_doc = frappe.get_doc("Selling Rate", rate_list[0].name)
					for x in rate_doc.package_rate:
						if x.weight >= row.actual_weight_per_parcel:
							amount += (x.rate * row.total_identical_parcels)
							count = 1
							break
						else:
							last_row_rate = x

					if count == 0:
						amount += ((last_row_rate.rate / last_row_rate.weight) * row.actual_weight_per_parcel) * row.total_identical_parcels
				else:
					frappe.throw(
						"Selling Rate List for <b>'{}'</b> is not Available for Today's Date to <b>{}</b> in <b>{}</b> through <b>{}</b> with <b>{}</b> service.".format(
							row.packaging_type, self.imp__exp, self.zone, self.mode_of_transportation, self.service_type))

			self.amount = amount
		
			






		
		# FSC	/  Optional Services
		if self.amount or self.amount==0 :

			fsc_doc = frappe.get_doc('Additional Charges Page')
			if fsc_doc :
				self.fsc = (self.amount + add_handling + ex_area + rem_area + lps + sat_del + max_ovr_lmt) * fsc_doc.feul_surcharge_percentage_on_freight_amount /100.0
			else :
				self.fsc = 0	

			self.freight = self.amount + self.total_additional_charges + self.fsc + self.sbc + self.insurance


			if self.discount_based_on == 'Percentage' :
				self.amount_after_discount = self.freight - (self.freight*self.discount_percentage)/100.0
			elif self.discount_based_on == 'Amount' :
				self.amount_after_discount = self.freight - self.discount_amount

		



		if self.amount_after_discount or self.amount_after_discount==0 :
			self.uls_selling_amount = self.amount_after_discount + self.total_additional_charges
			if self.ups_given_discount_in_percentage or self.ups_given_discount_in_percentage==0:
				self.ups_buying_amount = self.uls_selling_amount - (self.uls_selling_amount*self.ups_given_discount_in_percentage)/100.0



		if self.amount_after_discount > self.balance_credit_limit_before_shipment :
			frappe.throw("Your credit limit is not enough to make this shipment")
		else :
			self.balance_credit_limit_after_shipment = self.balance_credit_limit_before_shipment - self.amount_after_discount

		
		self.document_status = 'Draft'




		# token = generate_token()
		# data = label_recovery(token , 'eajc7asqid')
		# frappe.msgprint(data)
				




	# def after_insert(self) :
		# self.submit()


