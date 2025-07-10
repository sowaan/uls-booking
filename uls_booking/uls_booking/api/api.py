


import frappe
import json
from frappe.model.mapper import get_mapped_doc
import requests
import base64
from frappe import _
import zipfile
import io
from frappe.utils.pdf import get_pdf

def scrub(txt=None):
    if txt is None:
        return ""
    return txt.replace(' ', '_').lower()


@frappe.whitelist()
def download_sales_invoices_zip(docname, selected_customers):

    selected_customers = frappe.parse_json(selected_customers)
    if not selected_customers:
        frappe.throw("No customers selected")

    original_doc = frappe.get_doc("Sales Invoice PDF", docname)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for row in original_doc.customer_with_sales_invoice:
            if row.name not in selected_customers:
                continue

            single_doc = frappe.copy_doc(original_doc)
            single_doc.customer_with_sales_invoice = [row]

            frappe.flags.ignore_print_permissions = True
            html = frappe.get_print(
                "Sales Invoice PDF",
                single_doc.name,
                print_format="Specific Customer Sales Invoice Tax",
                doc=single_doc
            )

            pdf_data = get_pdf(html)
            filename = f"{scrub(row.customer)}_{row.name1}.pdf"
            zipf.writestr(filename, pdf_data)

    zip_buffer.seek(0)
    file_name = f"{docname}_customer_invoices.zip"
    frappe.local.response.filename = file_name
    frappe.local.response.filecontent = zip_buffer.getvalue()
    frappe.local.response.type = "download"




# @frappe.whitelist()
# def update_include_in_print(docname, selected_customers):
#     child_rows = frappe.get_all("Sales Invoice PDF table",
#         filters={"parent": docname},
#         fields=["name"]
#     )
#     for row in child_rows:
#         value = 1 if row.name in selected_customers else 0
#         frappe.db.set_value("Sales Invoice PDF table", row.name, "include_in_print", value)





@frappe.whitelist()
def get_address(customer):
    add = []
    add_list = frappe.get_list('Dynamic Link',
                    filters = {
                        'parenttype' : 'Address',
                        'link_name' : customer, 
                    }, fields = ['parent'],
                    ignore_permissions = True)
    if add_list:
        for x in add_list :
            add.append(x.parent)
        return add


@frappe.whitelist()
def get_cities(country) :
    city = []
    # frappe.msgprint(1)
    city_list = frappe.get_list('City',
                    filters = {
                        'country' : country,
                    },fields = ['name'],
                    ignore_permissions = True)
    if city_list:
        for x in city_list :
            city.append(x.name)
        return city


@frappe.whitelist()
def get_postal_codes(country) :
    postal_codes = []
    postal_codes_list = frappe.get_list('Postal Codes',
                    filters = {
                        # 'city' : city,
                        'country' : country,
                    },fields = ['name'],
                    ignore_permissions = True)
    if postal_codes_list:
        for x in postal_codes_list :
            postal_codes.append(x.name)
        return postal_codes
    

@frappe.whitelist()
def get_icris_accounts(customer) :
    cust = frappe.get_doc('Customer',customer)
    icris_accounts = []
    for account in cust.custom_icris_account :
        icris_accounts.append(account.icris_account)
    
    return icris_accounts    





@frappe.whitelist()
def get_service_types(customer,imp_exp_field) :
    cust = frappe.get_doc('Customer',customer)
    service_types = []

    # if imp_exp_field == 'Import' :
    if cust.custom_service_types :
        for row in cust.custom_service_types :
            if row.imp__exp == imp_exp_field :
                service_types.append(row.service_type)

    #     if cust.custom_express_plus == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Import Express Plus")
    #         service_types.append(ser_doc.name)
    #     if cust.custom_express_imp == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Import Express")
    #         service_types.append(ser_doc.name)

    #     if cust.custom_express_saver_imp == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Import Express Saver")
    #         service_types.append(ser_doc.name)

    #     if cust.custom_expedited_imp == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Import Express Saver")
    #         service_types.append(ser_doc.name)

    #     if cust.custom_express_freight_imp == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Import Express Freight")
    #         service_types.append(ser_doc.name)        

    # elif imp_exp_field == 'Export' :
    #     if cust.custom_express_plus_exp == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Export Express Plus")
    #         service_types.append(ser_doc.name)
    #     if cust.custom_express == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Export Express")
    #         service_types.append(ser_doc.name)

    #     if cust.custom_express_saver == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Export Express Saver")
    #         service_types.append(ser_doc.name)

    #     if cust.custom_expedited == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Export Expedited")
    #         service_types.append(ser_doc.name)

    #     if cust.custom_express_freight == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Export Express Freight")
    #         service_types.append(ser_doc.name)   

    #     if cust.custom_express_freight_midday == 1 :
    #         ser_doc = frappe.get_doc("Service Type","Export Express Freight Midday")
    #         service_types.append(ser_doc.name)            

    # for account in cust.service_types :
    #     service_types.append(account.service_type)
    
    return service_types   



@frappe.whitelist()
def get_email_table(email_id):
    cont = []
    email_list = frappe.get_list('Contact Email',
                    filters = {
                        'parenttype' : 'Contact',
                        'email_id' : email_id, 
                    }, fields = ['parent'],
                    ignore_permissions = True)
    if email_list:
        for x in email_list :
            cont.append(x.parent)
        return cont
        

@frappe.whitelist()
def get_customer(email_id) :
    # cont = []
    cust_list_1 = []
    customers_list = frappe.get_list("Portal User",
                            filters={
                                'parenttype' : 'Customer' ,
                                'user' : email_id ,
                            }, fields=['parent'],
                            ignore_permissions = True)
                       
    if customers_list :
        for c in customers_list :
            cust_list_1.append(c.parent)

        cust_list = tuple(cust_list_1)
        return cust_list





@frappe.whitelist()
def get_customer1(contact):
    cust_list_1 = []
    cont_doc = frappe.get_doc('Contact',contact)
    for y in cont_doc.links :
        cust_list_1.append(y.link_name)

    cust_list = tuple(cust_list_1)

    return cust_list
        
        
@frappe.whitelist()
def get_customer_doc(customer):
    cust = frappe.get_doc('Customer',customer)
    # frappe.msgprint(str(cust.name))
    name = cust.name
    return name




@frappe.whitelist()
def ic_label(add_charge_type,add_charge_check):
    add_charge_doc = frappe.get_doc('Additional Charges',add_charge_type)
    return add_charge_doc.amount
        


@frappe.whitelist()
def duty_tax(add_charge_type , impexp):
    add_charge_doc = frappe.get_doc('Additional Charges',add_charge_type)
    if impexp == 'Import' :
        return add_charge_doc.import_amount
    elif impexp == 'Export' :
        return add_charge_doc.export_amount       
                


@frappe.whitelist()
def area(add_charge_type, weight):
    add_charge_doc = frappe.get_doc('Additional Charges',add_charge_type)
    amount_per_kg = float(add_charge_doc.amount_per_kg)
    weight = float(weight)
    w = amount_per_kg * weight
    
    return max(add_charge_doc.amount_per_shipment, w)

        

@frappe.whitelist()
def add_handling( add_charge_type ,name) :
    add_charge_doc = frappe.get_doc('Additional Charges',add_charge_type)
    booking_doc = frappe.get_doc('Booking',name)
    # frappe.msgprint(str(booking_doc.name))

    actual_weight = 0
    no_of_pkg_for_avg = 0
    single_pkg_no = 0
    avg = 0
    for row in booking_doc.parcel_information :
        pkg_doc = frappe.get_doc("Package Types",row.packaging_type)
        if pkg_doc.package == 1 :
            no_of_pkg_for_avg = no_of_pkg_for_avg + row.total_identical_parcels
            actual_weight = actual_weight + row.actual_weight
            if row.actual_weight_per_parcel > add_charge_doc.max_weight :
                single_pkg_no = single_pkg_no + row.total_identical_parcels


    if no_of_pkg_for_avg > 0 :
        avg = actual_weight / no_of_pkg_for_avg         

    if avg > add_charge_doc.max_avg_weight :
        return max(no_of_pkg_for_avg*add_charge_doc.amount , add_charge_doc.minimum_amount )
    
    else :
        if single_pkg_no > 0 :
            return max(single_pkg_no*add_charge_doc.amount , add_charge_doc.minimum_amount )



@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False) :
    doclist = get_mapped_doc(
		"Booking",
		source_name,
		{
			"Booking": {
				"doctype": "Sales Invoice",
				"field_map": {
					"customer": "customer",
				},
				# "validation": {"docstatus": ["=", 1]},
			},
		},
		target_doc,
		ignore_permissions=ignore_permissions,
	)

    return doclist



@frappe.whitelist()
def get_credit_balance(customer, company) :

    booking_list = frappe.get_list("Booking",
                    filters={
                        'customer' : customer,
                        'company' : company,
                        'docstatus' : 1
                    }, fields=['name','amount_after_discount'],
                    ignore_permissions = True)

    total_credit_limit = 0
    credit_limit_used = 0
    balance_before_ship = 0

    if booking_list :
        for booking in booking_list :
            credit_limit_used = credit_limit_used + booking.amount_after_discount


    cust_doc = frappe.get_doc('Customer',customer)
    if cust_doc.credit_limits :
        for row in cust_doc.credit_limits :
            if row.company == company :
                total_credit_limit = row.credit_limit
                break


    balance_before_ship = total_credit_limit - credit_limit_used

    if balance_before_ship <= 0 :
        frappe.throw("Customer's Balance Credit Limit is zero.")
            
    else :
        return balance_before_ship
    









@frappe.whitelist()
def get_full_tariff(service_type) :

    full_tariff = []

    full_tariff_list = frappe.db.get_list("Full Tariff",
                       filters={
                           'service_type' : service_type
                       })
    if full_tariff_list:
        for x in full_tariff_list :
            full_tariff.append(x.name)
    
    return full_tariff



@frappe.whitelist()
def get_selling_rate_group(service_type) :

    s_r_grp = []

    s_r_grp_list = frappe.db.get_list("Selling Rate Group",
                       filters={
                           'service_type' : service_type
                       })
    if s_r_grp_list:
        for x in s_r_grp_list :
            s_r_grp.append(x.name)
    
    return s_r_grp





@frappe.whitelist()
def get_buying_rate_group(service_type) :

    b_r_grp = []

    b_r_grp_list = frappe.db.get_list("Buying Rate Group",
                       filters={
                           'service_type' : service_type
                       })
    if b_r_grp_list:
        for x in b_r_grp_list :
            b_r_grp.append(x.name)
    
    return b_r_grp




@frappe.whitelist()
def first_check_buying_rate(full_tariff , icris_account) :
    full_tariff_doc = frappe.get_doc("Full Tariff",full_tariff)
    rate = []

    if full_tariff_doc.based_on == 'Zone' :
        rate = frappe.db.exists("Buying Rate", 
                        {
                            "service_type" : full_tariff_doc.service_type , 
                            "icris_account" : icris_account , 
                            "based_on" : full_tariff_doc.based_on ,
                            "zone" : full_tariff_doc.zone ,
                            "mode_of_transportation" : full_tariff_doc.mode_of_transportation ,
                            "package_type" : full_tariff_doc.package_type ,
                            "import__export" : full_tariff_doc.import__export ,
                            "valid_from" : full_tariff_doc.valid_from ,
                            "expiry_date" : full_tariff_doc.expiry_date ,

                        })
    else :
        rate = frappe.db.exists("Buying Rate", 
                        {
                            "service_type" : full_tariff_doc.service_type , 
                            "icris_account" : icris_account , 
                            "based_on" : full_tariff_doc.based_on ,
                            "country" : full_tariff_doc.country ,
                            "mode_of_transportation" : full_tariff_doc.mode_of_transportation ,
                            "package_type" : full_tariff_doc.package_type ,
                            "import__export" : full_tariff_doc.import__export ,
                            "valid_from" : full_tariff_doc.valid_from ,
                            "expiry_date" : full_tariff_doc.expiry_date ,

                        })

    if rate :
        return 1
    else :
        return 2




@frappe.whitelist()
def check_for_existing_rate(full_tariff , weight_slab , rate_type , rate_grp, rate_creation_tool) :
    
    full_tariff_doc = frappe.get_doc("Full Tariff",full_tariff)
    rate = []


    if full_tariff_doc.based_on == 'Zone' :
        rate = frappe.db.exists(rate_type, 
                        {
                            "service_type" : full_tariff_doc.service_type , 
                            "rate_group" : rate_grp , 
                            "based_on" : full_tariff_doc.based_on ,
                            "zone" : full_tariff_doc.zone ,
                            "mode_of_transportation" : full_tariff_doc.mode_of_transportation ,
                            "package_type" : full_tariff_doc.package_type ,
                            "import__export" : full_tariff_doc.import__export ,
                            "valid_from" : full_tariff_doc.valid_from ,
                            "expiry_date" : full_tariff_doc.expiry_date ,

                        })

    else :
        rate = frappe.db.exists(rate_type, 
                        {
                            "service_type" : full_tariff_doc.service_type , 
                            "rate_group" : rate_grp , 
                            "based_on" : full_tariff_doc.based_on ,
                            "country" : full_tariff_doc.country ,
                            "mode_of_transportation" : full_tariff_doc.mode_of_transportation ,
                            "package_type" : full_tariff_doc.package_type ,
                            "import__export" : full_tariff_doc.import__export ,
                            "valid_from" : full_tariff_doc.valid_from ,
                            "expiry_date" : full_tariff_doc.expiry_date ,

                        })

    if rate :
        return rate
    else :
        create_rate(full_tariff , weight_slab , False, rate_type , rate_grp, rate_creation_tool)
        # return 0
        

@frappe.whitelist()
def create_rate(full_tariff , weight_slab, rate_type, rate_grp, rate_creation_tool ) :

    
    # weight_slab = json.loads(weight_slab)
    full_tariff_doc = frappe.get_doc("Full Tariff",full_tariff)


    ex_doc_name = frappe.db.exists({"doctype":rate_type , "rate_group":rate_grp , "full_tariff":full_tariff })
    
    
    if ex_doc_name :
        new_sell_rate = frappe.get_doc(rate_type,ex_doc_name)
        new_sell_rate.package_rate = []

    else :
        new_sell_rate = frappe.new_doc(rate_type)

    
    
    
    
    
    new_sell_rate.rate_group = rate_grp
    new_sell_rate.mode_of_transportation = full_tariff_doc.mode_of_transportation
    new_sell_rate.service_type = full_tariff_doc.service_type
    new_sell_rate.package_type = full_tariff_doc.package_type
    new_sell_rate.import__export = full_tariff_doc.import__export
    # new_sell_rate.valid_from = full_tariff_doc.valid_from
    # new_sell_rate.expiry_date = full_tariff_doc.expiry_date
    new_sell_rate.based_on = full_tariff_doc.based_on
    new_sell_rate.full_tariff = full_tariff_doc.name
    new_sell_rate.rate_creation_tool = rate_creation_tool

    for i in range(len(full_tariff_doc.package_rate)) :
        weight = full_tariff_doc.package_rate[i].weight
        rate = full_tariff_doc.package_rate[i].rate
        new_sell_rate.append('package_rate', {
            'weight': weight,
            'discount_percentage' : 0,
            'rate' : rate,
        })

        


    # new_sell_rate.package_rate = full_tariff_doc.package_rate

    if full_tariff_doc.based_on == 'Zone' :
        new_sell_rate.zone = full_tariff_doc.zone
    else :    
        new_sell_rate.country = full_tariff_doc.country


    for slab in weight_slab:
        from_weight = slab.from_weight
        to_weight = slab.to_weight
        percentage = slab.percentage

        for rate in new_sell_rate.package_rate:
            if from_weight <= rate.weight <= to_weight:
                rate.rate = rate.rate * (1 - percentage / 100)
                rate.discount_percentage = percentage


    # if exist != False :
    #     frappe.delete_doc(rate_type, exist)

    if ex_doc_name :
        new_sell_rate.save()
    else :    
        new_sell_rate.insert()
    frappe.msgprint("Rate Created.")
    # return 0


















@frappe.whitelist()
def generate_token(icris_account) :

    # base_url = "https://onlinetools.ups.com"
    # REMOVED
    # REMOVED

    booking_api_settings_doc = frappe.get_doc("Booking API Settings")

    base_url = booking_api_settings_doc.base_url
    version = booking_api_settings_doc.version

    auth_sig = 0

    if booking_api_settings_doc.icris_autherization :
        for icr in booking_api_settings_doc.icris_autherization :
            if icr.icris_account == icris_account :
                client_id = icr.client_id
                client_secret = icr.client_secret
                auth_sig = 1
                break

    if auth_sig == 0 :
        frappe.throw("Please define Client ID and Secret for respective ICRIS Account.")           




    credentials = f"{client_id}:{client_secret}"
    # print("Credentials : \n\n\n\n")
    # print(credentials)
    # print("\n\n\n\nCredentials : ")
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    url = f"{base_url}/security/{version}/oauth/token"
    # url = f"https://wwwcie.ups.com/security/{version}/oauth/token"
    # url = "https://onlinetools.ups.com/security/v1/oauth/token"

    payload = {
        "grant_type": "client_credentials",
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }

    response = requests.post(url, data=payload, headers=headers, auth=(client_id, client_secret))

    data = response.json()

    # you also have to handle error message if the coming response is not correct


    return data['access_token']



@frappe.whitelist()
def create_shipment(token , booking_name) :

    booking_doc = frappe.get_doc("Booking", booking_name)
    booking_api_settings_doc = frappe.get_doc("Booking API Settings")

    query = {
        'additionaladdressvalidation': 'string'
    }

    base_url = booking_api_settings_doc.base_url
    version = booking_api_settings_doc.version

    url = f"{base_url}/api/shipments/{version}/ship"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }


    # Shipper Info
    shipper = booking_doc.customer
    shipper_name = booking_doc.customer_name
    shipper_tax = frappe.db.get_value("Customer", booking_doc.customer , "tax_id")
    shipper_phone = frappe.db.get_value("Address" , booking_doc.address , "phone" )
    shipper_number = booking_doc.icris_account
    # shipper_number = '89R881',
    fax_number = frappe.db.get_value("Address" , booking_doc.address , "fax" )
    shipper_add_line = booking_doc.shipper_address
    shipper_city = booking_doc.shipper_city
    shipper_postal_code = booking_doc.shipper_postal_code
    shipper_country_code = frappe.db.get_value("Country" , booking_doc.shipper_country , "code" )



    # ShipFrom Info
    if booking_doc.is_customer1 == 1 :
        shipfrom = shipper
        shipfrom_name = shipper_name
        shipfrom_phone = shipper_phone
        shipfrom_fax_number = fax_number
        shipfrom_add_line = shipper_add_line
        shipfrom_city = shipper_city
        shipfrom_postal_code = shipper_postal_code
        shipfrom_country_code = shipper_country_code

    else :
        shipfrom = booking_doc.consignee_company_name
        shipfrom_name = booking_doc.attention_name1
        shipfrom_phone = booking_doc.consignee_phone
        shipfrom_fax_number = booking_doc.fax1
        shipfrom_add_line = booking_doc.consignee_address
        shipfrom_city = booking_doc.consignee_city
        shipfrom_postal_code = booking_doc.consignee_postal_code
        shipfrom_country_code = booking_doc.country_code_ship_from


    # ShipTo Info
    if booking_doc.is_customer == 1 :
        shipto = shipper
        shipto_name = shipper_name
        shipto_phone = shipper_phone
        shipto_add_line = shipper_add_line
        shipto_city = shipper_city
        shipto_postal_code = shipper_postal_code
        shipto_country_code = shipper_country_code
        shipto_state_province_code = booking_doc.state_province_code1

    else :
        shipto = booking_doc.name1
        shipto_name = booking_doc.attention_name
        shipto_phone = booking_doc.phone
        shipto_add_line = booking_doc.ship_to_address
        shipto_city = booking_doc.city
        shipto_postal_code = booking_doc.postal_code
        shipto_country_code = booking_doc.country_code
        shipto_state_province_code = booking_doc.state_province_code


    package_array = []
    pkg_nmbr = 0

    for row in booking_doc.parcel_information :
        for i in range(0,int(row.total_identical_parcels)) :
            pkg_nmbr = pkg_nmbr + 1
            package = {
                            "Description": 'Package '+ str(pkg_nmbr) ,
                            "Packaging": {
                                "Code": row.code,
                                "Description": row.packaging_type
                            },
                            "Dimensions": {
                                "UnitOfMeasurement": {
                                    "Code": 'CM',
                                    "Description": 'Centimeters'
                                },
                                "Length": str(row.length),
                                "Width": str(row.width),
                                "Height": str(row.height)
                            },
                            "PackageWeight": {
                                "UnitOfMeasurement": {
                                    "Code": 'KGS',
                                    "Description": 'Kilograms'
                                },
                                "Weight": str(row.actual_weight_per_parcel)
                            }
                    }

            package_array.append(package)
        

    body = {
        "ShipmentRequest": {
            "Request": {
                "SubVersion": '1801',
                "RequestOption": 'nonvalidate',
                "TransactionReference": {"CustomerContext": ''}
            },
            "Shipment": {
                "Description": 'Ship WS test',
                "Shipper": {
                    "Name": shipper,
                    "AttentionName": shipper_name,
                    "TaxIdentificationNumber": shipper_tax,
                    "Phone": {
                        "Number": shipper_phone,
                        "Extension": ' '
                    },
                    "ShipperNumber": shipper_number,
                    "FaxNumber": fax_number,
                    "Address": {
                        "AddressLine": [shipper_add_line],
                        "City": shipper_city,
                        # "StateProvinceCode": 'MD',
                        "PostalCode": shipper_postal_code,
                        "CountryCode": shipper_country_code
                    }
                },
                "ShipTo": {
                    "Name": shipto,
                    "AttentionName": shipto_name,
                    "Phone": {"Number": shipto_phone},
                    "Address": {
                        "AddressLine": [shipto_add_line],
                        "City": shipto_city,
                        "StateProvinceCode": shipto_state_province_code,
                        "PostalCode": shipto_postal_code,
                        "CountryCode": shipto_country_code
                    },
                    "Residential": ' '
                },
                "ShipFrom": {
                    "Name": shipfrom,
                    "AttentionName": shipfrom_name,
                    "Phone": {"Number": shipfrom_phone},
                    "FaxNumber": shipfrom_fax_number,
                    "Address": {
                        "AddressLine": [shipfrom_add_line],
                        "City": shipfrom_city,
                        # "StateProvinceCode": 'GA',
                        "PostalCode": shipfrom_postal_code,
                        "CountryCode": shipfrom_country_code
                    }
                },
                "PaymentInformation": {
                    "ShipmentCharge": {
                        "Type": '01',
                        "BillShipper": {"AccountNumber": shipper_number}
                    }
                },
                "Service": {
                    "Code": booking_doc.service_type_code,
                    "Description": 'Express'
                },
                "Package": package_array
            },
            "LabelSpecification": {
                "LabelImageFormat": {
                    "Code": "GIF",
                    "Description": "GIF"
                },
                "HTTPUserAgent": 'Mozilla/4.5'
            }
        }
    }

    response = requests.post(url, headers=headers, params=query, json=body)

    data = response.json()

    if 'response' in data and 'errors' in data['response']:
        error_message = data['response']['errors'][0]['message']
        booking_doc.shipping_error_log = error_message
        booking_doc.save()
        frappe.db.commit()
        # booking_doc.reload()
        # frappe.db.commit()
        frappe.throw(f"Shipment creation failed: {error_message}")

    else :    
        return data

   
    






@frappe.whitelist()
def label_recovery(token, booking_name) :
    	
    token = generate_token()

    version = "v1"
    url = "https://onlinetools.ups.com/api/labels/" + version + "/recovery"

    payload = {
    "LabelRecoveryRequest": {
        "LabelDelivery": {
        "LabelLinkIndicator": "",
        "ResendEmailIndicator": ""
        },
        "LabelSpecification": {
        "HTTPUserAgent": "Mozilla/4.5",
        "LabelImageFormat": {
            "Code": "ZPL"
        },
        "LabelStockSize": {
            "Height": "6",
            "Width": "4"
        }
        },
        "Request": {
        "RequestOption": "Non_Validate",
        "SubVersion": "1903",
        "TransactionReference": {
            "CustomerContext": ""
        }
        },
        "TrackingNumber": "1Z89R8810405766006",
        "Translate": {
        "Code": "01",
        "DialectCode": "US",
        "LanguageCode": "eng"
        }
    }
    }

    headers = {
    "Content-Type": "application/json",
    "transId": "string",
    "transactionSrc": "testing",
    "Authorization": "Bearer " + token
    }

    response = requests.post(url, json=payload, headers=headers)

    data = response.json()
    frappe.msgprint(str(data))
   


@frappe.whitelist()
def tracking(token, shipment_number) :


    booking_api_settings_doc = frappe.get_doc("Booking API Settings")
    inquiry_number = shipment_number
    version = booking_api_settings_doc.version
    base_url = booking_api_settings_doc.base_url

    url = base_url + "/api/track/" + version + "/details/" + inquiry_number

    query = {
    "locale": "en_US",
    "returnSignature": "false",
    "returnMilestones": "false",
    "returnPOD": "false"
    }

    headers = {
    "transId": "string",
    "transactionSrc": "testing",
    "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers, params=query)

    data = response.json()
    return data



@frappe.whitelist()
def cancel_shipment(token , booking_name) :


    booking_api_settings_doc = frappe.get_doc("Booking API Settings")
    booking_doc = frappe.get_doc("Booking" , booking_name)


    version = booking_api_settings_doc.version
    shipment_identification_number = frappe.db.get_value("Booking",booking_name,"shipment_identification_number")


    url = booking_api_settings_doc.base_url + "/api/shipments/" + version + "/void/cancel/" + shipment_identification_number
    headers = {
    'Content-Type': 'application/json',
    "Authorization": f'Bearer {token}'
    }

    response = requests.delete(url, headers=headers)

    data = response.json()


@frappe.whitelist()
def tracking_shipments() :
    
    booking_list = frappe.db.get_all("Booking",
                        filters={
                            'docstatus' : 1 ,
                            'booking_status' : 'Not Completed' ,
                        })

    if booking_list :
        for booking in booking_list :
            
            token = generate_token()
            inq_number = frappe.db.get_value("Booking",booking.name,"shipment_identification_number")                    
            data = tracking(token , inq_number)

            shipment_data = data.get('trackResponse', {}).get('shipment', [{}])[0].get('package', [{}])[0]

            current_status = shipment_data.get('currentStatus', {}).get('description')
            if current_status:
                frappe.db.set_value("Booking", booking.name, "current_status", current_status)

            current_status_code = shipment_data.get('currentStatus', {}).get('code')
            if current_status_code:
                frappe.db.set_value("Booking", booking.name, "current_status_code", current_status_code)


@frappe.whitelist()
def request_for_cancel(name) :
    frappe.db.set_value("Booking" , name , "document_status" , "Request For Cancel")
    return 1



@frappe.whitelist()
def check_user_permission(doc, method=None) :

    usrs = []
    for row in doc.portal_users :
        
        usrs.append(row.user)
        res = frappe.db.exists({"doctype": "User Permission", "user": row.user , "allow" : "Customer" , "for_value" : doc.name , "apply_to_all_doctypes" : 1})
        if not res :
            # frappe.msgprint("kon talha")
            us_p_doc = frappe.new_doc("User Permission")
            us_p_doc.user = row.user
            us_p_doc.allow = "Customer"
            us_p_doc.for_value = doc.name
            us_p_doc.apply_to_all_doctypes = 1
            us_p_doc.insert()



    us_p_list = frappe.db.get_list("User Permission",
                    filters={
                        "allow" : "Customer" ,
                        "for_value" : doc.name ,
                        "apply_to_all_doctypes" : 1 ,
                    },
                    fields=["name","user"]) 

    if us_p_list :
        
        for rec in us_p_list :
            if rec.user not in usrs :
                frappe.delete_doc('User Permission', rec.name)





@frappe.whitelist()
def get_full_tariff_with_rate_grp_wise(rate_group) :

    values = {
        'full_tariff_group' : rate_group ,
    } 

    result = frappe.db.sql("""

        SELECT
            ft.service_type AS 'service_type' ,
            ft.package_type AS 'package_type' ,
            ft.based_on AS 'based_on' ,
            ft.zone AS 'zone' ,
            ft.code AS 'country' ,
            pr.weight AS 'weight' ,
            pr.rate AS 'rate'

        FROM
            `tabFull Tariff` ft
            JOIN `tabPackage Rate` pr ON ft.name = pr.parent

        WHERE
            ft.full_tariff_group = %(full_tariff_group)s

        ORDER BY
            ft.name, pr.weight ASC       

    """,values=values , as_dict=1)



    return result


@frappe.whitelist()
def insert_rate_grp_from_erp(rec, full_tariff_group, doctype, rate_group) :   

    rec = json.loads(rec)

    if rec["based_on"] == 'Zone' :
        
        existing_rec = frappe.db.exists({"doctype": doctype, "rate_group": rate_group , "zone": rec["zone"] , "service_type": rec["service_type"] , "package_type": rec["package_type"] , })

        if existing_rec :
            # return existing_rec
            existing_rec_doc = frappe.get_doc(doctype , existing_rec)
            existing_rec_doc.full_tariff_group = full_tariff_group
            existing_rec_doc.package_rate = []
            for package in rec["package_rate"]:
                weight = package.get("weight")
                discount = package.get("percentage")
                rate = package.get("rate")

                existing_rec_doc.append('package_rate', {
                    'weight': float(weight),
                    'discount_percentage': float(discount),
                    'rate': float(rate),
                })
            existing_rec_doc.save()
            frappe.db.commit()


        else :
            new_rate = frappe.new_doc(doctype)
            new_rate.rate_group = rate_group
            new_rate.full_tariff_group = full_tariff_group
            new_rate.based_on = 'Zone'
            new_rate.zone = rec["zone"]
            new_rate.service_type = rec["service_type"]
            new_rate.package_type = rec["package_type"]
            for package in rec["package_rate"]:
                weight = package.get("weight")
                discount = package.get("percentage")
                rate = package.get("rate")

                new_rate.append('package_rate', {
                    'weight': float(weight),
                    'discount_percentage': float(discount),
                    'rate': float(rate),
                    'docstatus' : 0,
                })

            new_rate.insert()
            new_rate.save()
            frappe.db.commit()
             


    elif rec["based_on"] == 'Country' :
        
        country_list = frappe.db.get_list('Country',filters={
                            'code' : rec["country"]
                        })
        if country_list :
            country_doc = frappe.get_doc("Country" , country_list[0].name)

            existing_rec = frappe.db.exists({"doctype": doctype, "rate_group": rate_group , "country": country_doc.name , "service_type": rec["service_type"] , "package_type": rec["package_type"] , })

            if existing_rec :
                existing_rec_doc = frappe.get_doc(doctype , existing_rec)
                existing_rec_doc.package_rate = []
                for package in rec["package_rate"]:
                    weight = package.get("weight")
                    discount = package.get("percentage")
                    rate = package.get("rate")

                    existing_rec_doc.append('package_rate', {
                        'weight': float(weight),
                        'discount_percentage': float(discount),
                        'rate': float(rate),
                    })
                existing_rec_doc.save()
                frappe.db.commit()

            else :
                new_rate = frappe.new_doc(doctype)
                new_rate.rate_group = rate_group
                new_rate.full_tariff_group = full_tariff_group
                new_rate.based_on = 'Country'
                new_rate.country = country_doc.name
                new_rate.service_type = rec["service_type"]
                new_rate.package_type = rec["package_type"]
                for package in rec["package_rate"]:
                    weight = package.get("weight")
                    discount = package.get("percentage")
                    rate = package.get("rate")

                    new_rate.append('package_rate', {
                        'weight': float(weight),
                        'discount_percentage': float(discount),
                        'rate': float(rate),
                        'docstatus' : 0,
                    })

                new_rate.insert()
                new_rate.save()
                frappe.db.commit()


    return "Success"




@frappe.whitelist()
def insert_add_discount_rate_grp_from_erp(rec, full_tariff_group, doctype, rate_group) :
    
    rec = json.loads(rec)
    country_code = rec["country"]
    
    existing_rec_in_b_s = None

    country_list = frappe.get_list("Country", filters={
                        'code' : country_code
                    })
    if country_list :          
        country = country_list[0].name

        zone_list = frappe.get_list("Country Names", 
                        filters={
                            'countries' : country ,
                        },fields=['parent'],
                        ignore_permissions=True)
        
        if zone_list :
            zone = zone_list[0].parent
            for zn in zone_list :
                zone_doc = frappe.get_doc('Zone' , zn.parent)
                if zone_doc.is_single_country != 1 :
                    zone = zone_doc.name
                    break

 
            # existing_rec = frappe.db.exists({"doctype": "Full Tariff", "full_tariff_group": full_tariff_group , "based_on":"Zone", "zone": zone , "service_type": rec["service_type"] , "package_type": rec["package_type"] , })
            existing_rec = frappe.get_list("Full Tariff",
                                filters={
                                    "full_tariff_group": full_tariff_group ,
                                    "based_on":"Zone", 
                                    "zone": zone , 
                                    "service_type": rec["service_type"] , 
                                    "package_type": rec["package_type"]
                                }
                            )
            
            
            if existing_rec :
                existing_rec_doc = frappe.get_doc('Full Tariff' , existing_rec[0].name)

                # existing_rec_in_b_s = frappe.db.exists({"doctype": doctype, "rate_group": rate_group , "based_on":"Country", "country": country , "service_type": rec["service_type"] , "package_type": rec["package_type"] , })
                existing_rec_in_b_s = frappe.get_list(doctype, 
                                            filters={
                                                "rate_group": rate_group , 
                                                "based_on":"Country", 
                                                "country": country , 
                                                "service_type": rec["service_type"] , 
                                                "package_type": rec["package_type"]
                                            }
                                      )
                
                # return existing_rec_in_b_s

                if existing_rec_in_b_s :
                    buy_sell_doc = frappe.get_doc(doctype , existing_rec_in_b_s[0].name)
                    buy_sell_doc.full_tariff_group = full_tariff_group
                    buy_sell_doc.package_rate = []
                    for package in rec["package_rate"]:
                        weight = package.get("weight")
                        discount = package.get("percentage")
                        rate = package.get("rate")

                        for r in existing_rec_doc.package_rate :
                            if float(r.weight) == float(weight) :
                                rate = float(r.rate) * ( 1 - float(discount) / 100 )

                                buy_sell_doc.append('package_rate', {
                                    'weight': float(weight),
                                    'discount_percentage': float(discount),
                                    'rate': float(rate),
                                })
                                break

                    buy_sell_doc.save()
                    frappe.db.commit()


                else :
                    new_rate = frappe.new_doc(doctype)
                    new_rate.rate_group = rate_group
                    new_rate.full_tariff_group = full_tariff_group
                    new_rate.based_on = 'Country'
                    new_rate.country = country
                    new_rate.service_type = rec["service_type"]
                    new_rate.package_type = rec["package_type"]
                    
                    for package in rec["package_rate"]:
                        weight = package.get("weight")
                        discount = package.get("percentage")
                        rate = package.get("rate")

                        for r in existing_rec_doc.package_rate :
                            if float(r.weight) == float(weight) :
                                rate = float(r.rate) * ( 1 - float(discount) / 100 )

                                new_rate.append('package_rate', {
                                    'weight': float(weight),
                                    'discount_percentage': float(discount),
                                    'rate': float(rate),
                                    'docstatus' : 0,
                                })
                                break

                    new_rate.insert()
                    new_rate.save()
                    frappe.db.commit()



    return "Success"






            

        
        









