from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import getdate
import json
import re
from datetime import datetime


def generate_sales_invoice_enqued(doc_str,doc,shipments,definition_record,name):
    try:
        
       
        # doc = json.loads(doc_str)
        final_rate = 0
        tarif = 0
        # name = doc['name']
        discounted_amount = 0
        selling_rate_zone = None
        selling_rate_country = 0
        arrayy=[]
        # definition_record = doc.get("sales_invoice_definition")
        sales_name= []
        try:
            definition = frappe.get_doc("Sales Invoice Definition", definition_record)
        except frappe.DoesNotExistError:
            frappe.throw(frappe._("Sales Invoice Definition does not exist"))
        except frappe.PermissionError:
            frappe.throw(frappe._("You do not have permission to access the Sales Invoice Definition"))
        except Exception as e:
            frappe.throw(frappe._("Error fetching Sales Invoice Definition: ") + str(e))

        
        shipment = doc.get("shipment_numbers", "")
        frappe.db.set_value("Generate Sales Invoice",name,"status","In Progress")
        shipments = [value.strip() for value in shipment.split(",") if value.strip()]
        setting = frappe.get_doc("Manifest Setting Definition")
        excluded_codes = []
        included_codes=[]
    
        export_billing_term = []
        import_billing_term = []
        for term in definition.export_and_import_conditions:
            if term.export_check == 1:
                export_billing_term.append(term.billing_term)

            elif term.export_check == 0:
                import_billing_term.append(term.billing_term)
        for code in setting.surcharges_code_excl_and_incl:

            excluded_codes.append(code.excluded_codes)
            included_codes.append(code.included_codes)
       
        for shipment in shipments:
          
            discounted_amount = discounted_amount +1
            final_rate = 0
            tarif = 0
            signal = 0
            customer_signal =0
            final_discount_percentage = 0
            selected_weight = 0
            checkship = frappe.get_list("Sales Invoice",
                                        filters = {"custom_shipment_number":shipment})
            if checkship:
                frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "Sales Invoice Already present",
                                            "error": f"""Shipment Number:,{shipment}"""
                                        }).insert()
                continue
            
            sales_invoice = frappe.new_doc("Sales Invoice")
            
            company = definition.default_company
            customer = frappe.get_doc("Company",company,
            fields = ["custom_default_customer"])
            sales_invoice.customer = customer.custom_default_customer
            doctype_name =0
            total_charges_incl_fuel = 0
            total_charges_other_charges = 0
            FSCcharges = 0
            FSCpercentage = 0
            shipment_type = 0
            for child_record in definition.sales_invoice_definition:
                doctype_name = child_record.ref_doctype
                field_name = child_record.field_name
                sales_field_name = child_record.sales_invoice_field_name

                
                docs = frappe.get_list(
                    doctype_name,
                    filters={'shipment_number': shipment},
                    fields=[field_name]
                )
                
                if docs:
                   
                    sales_invoice.set(sales_field_name, docs[0][field_name])
                    sales_invoice.posting_date = sales_invoice.custom_date_shipped
                    posting_date = getdate(sales_invoice.posting_date)
                    sales_invoice.set_posting_time = 1
                    # sales_invoice.due_date = sales_invoice.posting_date
                   
            
            icris_number = None
            selling_group = None
            selling_rate = None
            
            if sales_invoice.custom_shipper_country == definition.origin_country.upper():
                imp_exp = "Export"
                if sales_invoice.custom_shipper_number:
                    icris_number = sales_invoice.custom_shipper_number
                else:
                    icris_number = definition.unassigned_icris_number

            elif sales_invoice.custom_shipper_country != definition.origin_country.upper():
                imp_exp = "Import"
                if sales_invoice.custom_consignee_number:
                    icris_number = sales_invoice.custom_consignee_number
                else:
                    icris_number = definition.unassigned_icris_number

            
            weight_frm_R200000 = frappe.get_value(
                "R202000",
                filters={'shipment_number': shipment},
                fieldname="custom_expanded_shipment_weight"
            )

            weight_frm_R201000 = frappe.get_value(
                "R201000",
                filters={'shipment_number': shipment},
                fieldname="custom_minimum_bill_weight"
            )

           
            weight_frm_R200000 = float(weight_frm_R200000) if weight_frm_R200000 else 0.0
            weight_frm_R201000 = float(weight_frm_R201000) if weight_frm_R201000 else 0.0

           
            selected_weight = max(weight_frm_R200000, weight_frm_R201000)
            sales_invoice.custom_shipment_weight = selected_weight

            if sales_invoice.custom_package_type:
                for code in definition.package_type_replacement:
                    if sales_invoice.custom_package_type == code.package_type_code:
                        sales_invoice.custom_package_type = code.package_type
                        shipment_type = sales_invoice.custom_package_type
                        break
            
                
            else:
                shipment_type = sales_invoice.custom_shipment_type
            try:
                icris_account = frappe.get_doc("ICRIS Account", icris_number)
               
            except frappe.DoesNotExistError:
                
                print("ICRIS Account does not exist. and the Icris number is :" , icris_number , "The shipment Number :", sales_invoice.custom_shipment_number,"\n \n")
                frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No ICRIS ACCOUNT",
                                            "error": f"""Shipment Number:,{shipment},Icris Number: {icris_number}"""
                                        }).insert()
                continue            
            except Exception as e:
                print(f"An error occurred: {str(e)}")
            
            
            
            if sales_invoice.custom_billing_term in export_billing_term and sales_invoice.custom_shipper_country == definition.origin_country.upper():
                check1 = frappe.get_list("ICRIS List",
                                        filters = {"shipper_no":icris_number})
                
                if check1:
                    
                    icris = frappe.get_doc("ICRIS List",check1[0].name)
                    if icris.shipper_name:
                        sales_invoice.customer = icris.shipper_name
                    else:
                        frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No Customer Found",
                                            "error": f"""Shipment Number:,{shipment},Icris Number: {icris_number}"""
                                        }).insert()
                    
                
                    print(sales_invoice.customer)
                    tt = frappe.get_doc("Territory", {"name": sales_invoice.custom_shipper_city})
                    pt = tt.parent_territory
                    if pt != "All Territories":
                        stc = frappe.get_doc("Sales Taxes and Charges Template", {"custom_province": pt})
                        for sale in stc.taxes:
                            charge_type = sale.charge_type
                            description = sale.description
                            account_head = sale.account_head
                            cost_center = sale.cost_center
                            rate = sale.rate
                            account_currency = sale.account_currency
                        sales_invoice.set("taxes_and_charges", stc.name)
                        rows = {'charge_type': charge_type, 'description': description, 'account_head': account_head, 'cost_center':cost_center, 'rate':rate, 'account_currency':account_currency}
                        sales_invoice.append('taxes', rows)

                    
                    if sales_invoice.custom_consignee_country:
                        origin_country = sales_invoice.custom_consignee_country
                        origin_country = origin_country.capitalize()
                        
                    
                    zone_with_out_country = None
                    
                    selling_rate_name = None
                    
                    service_type = frappe.get_list("Service Type",
                                        filters = {"imp__exp":imp_exp , "service": sales_invoice.custom_service_type})
                    if service_type:
                        for icris in icris_account.rate_group:

                            if  icris.service_type == service_type[0].get("name")  and icris.from_date <= posting_date and posting_date <= icris.to_date :
                                selling_group = icris.rate_group
                                
                                break
                            
                        if not selling_group:
                            
                            frappe.get_doc({
                                        "doctype": "Error Log",
                                        "method": "No Selling Group For Export",
                                        "error": f"""Shipment Number:,{shipment},Selling Group: {selling_group} , Icris Number: {icris_number}"""
                                    }).insert()       
                                
                    
                    if selling_group:
                        
                        zones = frappe.get_list("Zone",
                                                filters = {"country" : origin_country , "is_single_country":1})
                        
                        flag = 0
                        if zones:
                            sales_invoice.custom_zone = zones[0].name
                            selling_rate_name = frappe.get_list("Selling Rate",
                                filters={
                                    "country": origin_country,
                                    "service_type": service_type[0].get("name"),
                                    "package_type": shipment_type,
                                    "rate_group": selling_group 
                                }
                            )
                        
                            if selling_rate_name:        
                                selling_rate_country = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                selling_rate = selling_rate_country
                                
                            else :
                                
                                flag = 1
                            
                        elif not zones:
                            flag = 1

                        if flag == 1 :

                            countries = frappe.db.get_all("Country Names", filters={"countries":origin_country} , fields = ['parent'])
                            
                            if countries:
                                zone_with_out_country = countries[0].parent
                                if zone_with_out_country:
                                    sales_invoice.custom_zone = zone_with_out_country
                                    selling_rate_name = frappe.get_list("Selling Rate",
                                        filters={
                                            "zone": zone_with_out_country,
                                            "service_type": service_type[0].get("name"),
                                            "package_type": shipment_type,
                                            "rate_group": selling_group 
                                        }
                                    )
                                
                                    
                                    if selling_rate_name:        
                                        selling_rate_zone = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                        selling_rate = selling_rate_zone
                                        
                                    else :
                                        frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No Selling Rate Found",
                                            "error": f"""No Selling Rate Found The shipment nummber is : ,{sales_invoice.custom_shipment_number} , Zone:, {zone_with_out_country} , Service Type : ,  {service_type[0].get("name")} , Package type :,{shipment_type }, Selling Group : {selling_group}, Icris Number : {icris_number}"""
                                        }).insert()
                                        
                                        continue
                            else:


                                frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No Country Found",
                                            "error": f"""Shipment Number:,{shipment},Shipper Country: {origin_country}"""
                                        }).insert()


                                
                                continue            
                        
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        if selling_rate :

                            flg = 0
                            last_row = {}

                            for row in selling_rate.package_rate :

                                if my_weight <= row.weight :
                                    final_rate = row.rate
                                    final_discount_percentage = row.discount_percentage
                                    flg = 1
                                    break
                                else :
                                    last_row = row

                            if flg == 0 :
                                final_rate = ( last_row.rate / last_row.weight ) * my_weight
                                final_discount_percentage = last_row.discount_percentage


                            tarif = final_rate / (1- (final_discount_percentage/100))
            elif sales_invoice.custom_billing_term in import_billing_term and sales_invoice.custom_shipper_country != definition.origin_country.upper():
               
                
                check = frappe.get_list("ICRIS List",
                                        filters = {"shipper_no":icris_number})
                if check:
                    icris1 = frappe.get_doc("ICRIS List",check[0].name)
                    if icris1.shipper_name:
                        sales_invoice.customer = icris1.shipper_name
                    else:
                        frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No Customer Found",
                                            "error": f"""Shipment Number:,{shipment},Icris Number: {icris_number}"""
                                        }).insert()
                        
                
                    print(sales_invoice.customer)
                    mm = frappe.get_doc("Territory", {"name": sales_invoice.custom_consignee_city})
                    vv = mm.parent_territory
                    
                    if vv != "All Territories":
                        bb = frappe.get_doc("Sales Taxes and Charges Template", {"custom_province": vv})
                        sales_invoice.set("taxes_and_charges", bb.name)
                        for sale in bb.taxes:
                            charge_type = sale.charge_type
                            description = sale.description
                            account_head = sale.account_head
                            cost_center = sale.cost_center
                            rate = sale.rate
                            account_currency = sale.account_currency
                        rows = {'charge_type': charge_type, 'description': description, 'account_head': account_head, 'cost_center':cost_center, 'rate':rate, 'account_currency':account_currency}
                        sales_invoice.append('taxes', rows)

                    if sales_invoice.custom_shipper_country:
                        origin_country = sales_invoice.custom_shipper_country
                        origin_country = origin_country.capitalize()
                        
                    
                    zone_with_out_country = None
                    
                    selling_rate_name = None
                    
                    service_type = frappe.get_list("Service Type",
                                        filters = {"imp__exp":imp_exp , "service": sales_invoice.custom_service_type})
                    
                    if service_type:
                        for icris in icris_account.rate_group:
                            if  icris.service_type == service_type[0].get("name")  and icris.from_date <= posting_date <= icris.to_date:
                                selling_group = icris.rate_group
                                break
                        if not selling_group:
                            
                            frappe.get_doc({
                                        "doctype": "Error Log",
                                        "method": "No Selling Group For Import",
                                        "error": f"""Shipment Number:,{shipment},Selling Group: {selling_group} , Icris Number: {icris_number}"""
                                    }).insert()
                            
                    
                    if selling_group:
                        
                        zones = frappe.get_list("Zone",
                                                filters = {"country" : origin_country , "is_single_country":1})
                        
                        flag = 0
                        if zones:
                            sales_invoice.custom_zone = zones[0].name
                            print("Zone with Country :",zones[0].name)
                            selling_rate_name = frappe.get_list("Selling Rate",
                                filters={
                                    "country": origin_country,
                                    "service_type": service_type[0].get("name"),
                                    "package_type": shipment_type,
                                    "rate_group": selling_group 
                                }
                            )
                        
                            if selling_rate_name:        
                                selling_rate_country = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                selling_rate = selling_rate_country
                                
                            else :
                                
                                flag = 1
                            
                        elif not zones:
                            flag = 1

                        if flag == 1 :

                            countries = frappe.db.get_all("Country Names", filters={"countries":origin_country} , fields = ['parent'])
                            
                            if countries:
                                zone_with_out_country = countries[0].parent
                                if zone_with_out_country:
                                    sales_invoice.custom_zone = zone_with_out_country
                                    print("Zone with Out Country :",zone_with_out_country)
                                    selling_rate_name = frappe.get_list("Selling Rate",
                                        filters={
                                            "zone": zone_with_out_country,
                                            "service_type": service_type[0].get("name"),
                                            "package_type": shipment_type,
                                            "rate_group": selling_group 
                                        }
                                    )
                                
                                    
                                    if selling_rate_name:        
                                        selling_rate_zone = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                        selling_rate = selling_rate_zone
                                        
                                    else :
                                        frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No Selling Rate Found",
                                            "error": f"""No Selling Rate Found The shipment nummber is : ,{sales_invoice.custom_shipment_number} , Zone:, {zone_with_out_country} , Service Type : ,  {service_type[0].get("name")} , Package type :,{shipment_type }, Selling Group : {selling_group}, Icris Number : {icris_number}"""
                                        }).insert()
                                    
                                        
                                        continue
                            else:
                                frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "No Country Found",
                                            "error": f"""Shipment Number:,{shipment},Shipper Country: {origin_country}"""
                                        }).insert()
                                continue            
                        
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        if selling_rate :

                            flg = 0
                            last_row = {}

                            for row in selling_rate.package_rate :

                                if my_weight <= row.weight :
                                    final_rate = row.rate
                                    final_discount_percentage = row.discount_percentage
                                    flg = 1
                                    break
                                else :
                                    last_row = row

                            if flg == 0 :
                                final_rate = ( last_row.rate / last_row.weight ) * my_weight
                                final_discount_percentage = last_row.discount_percentage


                            tarif = final_rate / (1- (final_discount_percentage/100))

            currency = frappe.get_value("Customer" , sales_invoice.customer , "default_currency") 
            sales_invoice.currency = currency
            codes_incl_fuel = []
            amounts_incl_fuel = []
            surcharge_codes_incl_fuel = []

            codes_other_charges = []
            amounts_other_charges = []
            surcharge_codes_other_charges = []

            if doctype_name:
               
                r201 = frappe.get_list(
                    "R201000",
                    filters={'shipment_number': shipment},
                )
                if r201:
                    docn = frappe.get_doc("R201000", r201[0].name)

                    for row in definition.surcharges:
                        code_name = row.sur_cod_1
                        amount_name = row.sur_amt_1

                        
                        code = getattr(docn, code_name, None)
                        amount = getattr(docn, amount_name, None)

                        
                        try:
                            amount = float(amount)
                        except (ValueError, TypeError):
                            amount = 0 

                    
                        if code in included_codes and code not in excluded_codes:
                            
                            if code: 
                                codes_incl_fuel.append(code)
                                amounts_incl_fuel.append(amount)
                                surcharge_codes_incl_fuel.append(code_name)
                        elif code not in excluded_codes and code not in included_codes:
                            
                            if code:  
                                codes_other_charges.append(code)
                                amounts_other_charges.append(amount)
                                surcharge_codes_other_charges.append(code_name)

                
                sales_invoice.custom_surcharge_excl_fuel = []
                total_charges_incl_fuel = sum(amounts_incl_fuel)
                total_charges_other_charges = sum(amounts_other_charges)
                for surcharge_code, code, amount in zip(surcharge_codes_other_charges, codes_other_charges, amounts_other_charges):
                    if code: 
                        sales_invoice.append("custom_surcharge_excl_fuel", {
                            "surcharge": surcharge_code, 
                            "code": code,                
                            "amount": amount             
                        })
                sales_invoice.custom_surcharge_incl_fuel = []

                for surcharge_code, code, amount in zip(surcharge_codes_incl_fuel, codes_incl_fuel, amounts_incl_fuel):
                    if code: 
                        sales_invoice.append("custom_surcharge_incl_fuel", {
                            "surcharge": surcharge_code,  
                            "code": code,                
                            "amount": amount            
                        })
                
                sales_invoice.custom_total_surcharges_excl_fuel = total_charges_other_charges
                sales_invoice.custom_total_surcharges_incl_fuel = total_charges_incl_fuel
                FSCpercentage = frappe.db.get_value('Additional Charges', 'Fuel Surcharge', 'percentage')
                if FSCpercentage and tarif:
                        FSCcharges = (total_charges_incl_fuel + final_rate) * (FSCpercentage / 100 )
            shipmentbillingcheck = 0
            shipmentbillingamount = 0
            shipmentbillingchargesfromcustomer = 0
            if sales_invoice.customer:
                shipmentbillingcheck = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipping_bill_charges_applicable')
                shipmentbillingchargesfromcustomer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipment_billing_charges')
                if shipmentbillingcheck and not shipmentbillingchargesfromcustomer:
                    if imp_exp == "Export":
                        shipmentbillingamount = frappe.db.get_value('Additional Charges', 'Shipping Bill Charges', 'export_amount')
                        
                    elif imp_exp == "Import":
                        shipmentbillingamount = frappe.db.get_value('Additional Charges', 'Shipping Bill Charges', 'import_amount')
                elif shipmentbillingcheck and shipmentbillingchargesfromcustomer:
                    shipmentbillingamount = shipmentbillingchargesfromcustomer

            declared_value = sales_invoice.custom_insurance_amount
            decalred_value = 0  
            if isinstance(declared_value, (int, float)):
                declared_value = float(declared_value)
            elif isinstance(declared_value, str):
                stripped_value = declared_value.strip()
                
                
                try:
                    declared_value = float(stripped_value) 
                except ValueError:
                    print("")
                   
            else:
                print("")
                
            max_insured = 0
            if sales_invoice.customer != customer.custom_default_customer:
                
                if decalred_value > 0:
                    
                    percent = frappe.db.get_value('Additional Charges', 'Declare Value', 'percentage')
                    minimum_amount = frappe.db.get_value('Additional Charges', 'Declare Value', 'minimum_amount')
                    result = decalred_value * (percent / 100)
                    max_insured = max(result , minimum_amount)
                    
                    if max_insured > 0 and shipment_type == setting.insurance_shipment_type:
                        rows = {'item_code': setting.insurance_charges, 'qty': '1', 'rate': max_insured}
                        
                        sales_invoice.append('items', rows)

                
                sales_invoice.discount_amount = tarif - final_rate
                sales_invoice.custom_selling_percentage = final_discount_percentage


                if total_charges_other_charges:
                    rows = {'item_code': setting.other_charges, 'qty': 1} 
                    
                    sales_invoice.append('items', rows)
                if FSCcharges:
                    rows = {'item_code': setting.fuel_charges, 'qty': '1', 'rate': FSCcharges}
                    
                    sales_invoice.append('items', rows)
                if tarif:
                    rows = {'item_code' : setting.freight_charges , 'qty' : '1' , 'rate' : tarif}
                    
                    sales_invoice.append('items' , rows)
                if shipmentbillingamount:
                    rows = {'item_code' : setting.shipment_billing_charges , 'qty' : '1' , 'rate' : shipmentbillingamount}
                    
                    sales_invoice.append('items' , rows)

            export_compensation_amount = 0
            
            if sales_invoice.customer == customer.custom_default_customer:
                
                sig = 0
                for comp in definition.compensation_table:
                    if sales_invoice.custom_billing_term == comp.shipment_billing_term and shipment_type == comp.shipping_billing_type and imp_exp == comp.case:
                        export_compensation_amount = comp.document_amount
                        
                        rows = {'item_code': setting.compensation_charges , 'qty': '1', 'rate': export_compensation_amount}
                        sales_invoice.append('items', rows)
                        sig = 1
                        break
    
            if not sales_invoice.items:
                
                print("shipment number" , sales_invoice.custom_shipment_number , "Item table is empty, so cannot make Sales Invoice. icris :",icris_number,"\n\n\n")
                frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "N0 Items",
                                            "error": f"""{sales_invoice.custom_shipment_number}, Icris Number:{icris_number}"""
                                        }).insert()
                continue
            
            discounted_amount = discounted_amount -1
            sales_invoice.insert()
            sales_name.append(sales_invoice.name)
            
            for row in doc["shipment_numbers_and_sales_invoices"]:
                if sales_invoice.custom_shipment_number == row['shipment_number']:  # Change row.shipment_number to row['shipment_number']
                    frappe.db.set_value("Shipment Numbers And Sales Invoices", row['name'], "sales_invoice", sales_invoice.name)

            sales_invoice.save()
            if sales_invoice.customer != customer.custom_default_customer:
                for row in sales_invoice.items:
                    if row.item_code == setting.other_charges:
                    
                        frappe.db.set_value(row.doctype , row.name ,"rate" , total_charges_other_charges )
                        frappe.db.set_value(row.doctype , row.name ,"amount" , total_charges_other_charges )
                        frappe.db.set_value(row.doctype , row.name ,"base_amount" , total_charges_other_charges )
                        frappe.db.set_value(row.doctype , row.name ,"base_rate" , total_charges_other_charges )
                frappe.db.set_value(sales_invoice.doctype , sales_invoice.name ,"total" , total_charges_other_charges +  FSCcharges + tarif + max_insured + shipmentbillingamount )
                frappe.db.set_value(sales_invoice.doctype , sales_invoice.name ,"grand_total" , total_charges_other_charges +  FSCcharges + tarif + max_insured + shipmentbillingamount)
        ship_numbers = ', '.join(sales_name)
        frappe.db.set_value("Generate Sales Invoice",name,"sales_invoices",ship_numbers)
        frappe.db.set_value("Generate Sales Invoice",name,"status","Generated")
        
               


        print(discounted_amount)
    except json.JSONDecodeError:
        frappe.throw(frappe._("Invalid JSON data"))
    except Exception as e:
        frappe.throw(frappe._("An error occurred: ") + str(e))




def chunk_list(lst, chunk_size):
    """Split a list into chunks of a specified size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

        
@frappe.whitelist()
def generate_sales_invoice(doc_str):
    doc = json.loads(doc_str)
    name = doc['name']
    definition_record = doc.get("sales_invoice_definition")
    shipment = doc.get("shipment_numbers", "")
    shipments = [value.strip() for value in shipment.split(",") if value.strip()]
    chunk_size = 15  # Adjust as needed

    # Enqueue each chunk of shipments
    for shipment_chunk in chunk_list(shipments, chunk_size):
        enqueue(
            generate_sales_invoice_enqued,
            doc_str=doc_str,
            doc=doc,
            shipments=shipment_chunk,
            definition_record=definition_record,
            name=name,
            queue="default"
        )
        frappe.db.commit()
    
    # generate_sales_invoice_enqued(doc_str)
    # enqueue(generate_sales_invoice_enqued, doc_str=doc_str,doc = doc, shipments = shipments,definition_record = definition_record, name = name, queue="default")
    
   




















def storing_shipment_number(arrays, frm, to, doc):

    
    shipment_numbers = set()  # Use a set to ensure uniqueness

    for line in arrays:
        try:
            shipment_num = line[frm:to].strip()
            if shipment_num:
                shipment_numbers.add(shipment_num)  # Add to the set
        except IndexError:
            frappe.log_error(f"IndexError processing line: {line}", "Data Processing Error")
            continue
        except Exception as e:
            frappe.log_error(f"Unexpected error processing line: {line}. Error: {str(e)}", "Data Processing Error")
            continue

    unique_shipment_numbers = list(shipment_numbers)
    # defintion = frappe.get_doc("Sales Invoice Definition", "4f1330rq6u")
    setting = frappe.get_doc("Manifest Setting Definition")
    origin_country = setting.origin_country
    for shipment in unique_shipment_numbers:
        # Check if the shipment number already exists
        existing_doc = frappe.get_value("Shipment Number", {"shipment_number": shipment})
        if existing_doc:
            billing_term = frappe.get_value("R200000", {"shipment_number": shipment}, "billing_term_field")
            date_shipped = frappe.get_value("R200000", {"shipment_number": shipment}, "shipped_date")
            shipment_doc = frappe.get_doc("Shipment Number",shipment)
            customer = None
            icris_number = None
            billing_type = None
            station = None
            # Fetch export shipments
            export_array_temp = frappe.get_list("R300000",
                filters=[
                    ["shipper_country", "=", origin_country],
                    ["shipment_number", "=", shipment]
                ],
                fields=["shipment_number", "shipper_number"]
            )

            if export_array_temp:
                station = frappe.get_value("R300000", {"shipment_number": shipment}, "shipper_city")
                shipper_number = export_array_temp[0].shipper_number
                icris = frappe.get_list("ICRIS List",
                    filters=[
                        ["shipper_no", "=", shipper_number]
                    ],
                    fields=["shipper_name", "shipper_no"]
                )
                if icris:
                    customer = icris[0].shipper_name
                    billing_type = frappe.get_value("Customer", icris[0].shipper_name, "custom_billing_type")
                    icris_number = icris[0].shipper_no

            # Fetch import shipments
            import_array_temp = frappe.get_list("R400000",
                filters=[
                    ["consignee_country_code", "=", origin_country],
                    ["shipment_number", "=", shipment]
                ],
                fields=["shipment_number", "consignee_number"]
            )

            if import_array_temp:
                station = frappe.get_value("R400000", {"shipment_number": shipment}, "consignee_city")
                consignee_number = import_array_temp[0].consignee_number
                icris = frappe.get_list("ICRIS List",
                    filters=[
                        ["shipper_no", "=", consignee_number]
                    ],
                    fields=["shipper_name", "shipper_no"]
                )
                if icris:
                    customer = icris[0].shipper_name
                    billing_type = frappe.get_value("Customer", icris[0].shipper_name, "custom_billing_type")
                    icris_number = icris[0].shipper_no


            # Create a new shipment document
            
            shipment_doc.set("shipment_number", shipment)
            shipment_doc.set("customer", customer)
            shipment_doc.set("date_shipped", date_shipped)
            shipment_doc.set("station", station)
            shipment_doc.set("icris_number", icris_number)
            shipment_doc.set("billing_type", billing_type)
            shipment_doc.set("billing_term",billing_term)
            # shipment_doc.insert()
            shipment_doc.save()
            frappe.db.commit()
                # continue  # Skip if it already exists
        else:
            date_shipped = frappe.get_value("R200000", {"shipment_number": shipment}, "shipped_date")
            billing_term = frappe.get_value("R200000", {"shipment_number": shipment}, "billing_term_field")
            customer = None
            icris_number = None
            billing_type = None
            station = None
            # Fetch export shipments
            export_array_temp = frappe.get_list("R300000",
                filters=[
                    ["shipper_country", "=", origin_country],
                    ["shipment_number", "=", shipment]
                ],
                fields=["shipment_number", "shipper_number"]
            )

            if export_array_temp:
                station = frappe.get_value("R300000", {"shipment_number": shipment}, "shipper_city")
                shipper_number = export_array_temp[0].shipper_number
                icris = frappe.get_list("ICRIS List",
                    filters=[
                        ["shipper_no", "=", shipper_number]
                    ],
                    fields=["shipper_name", "shipper_no"]
                )
                if icris:
                    customer = icris[0].shipper_name
                    billing_type = frappe.get_value("Customer", icris[0].shipper_name, "custom_billing_type")
                    icris_number = icris[0].shipper_no

            # Fetch import shipments
            import_array_temp = frappe.get_list("R400000",
                filters=[
                    ["consignee_country_code", "=", origin_country],
                    ["shipment_number", "=", shipment]
                ],
                fields=["shipment_number", "consignee_number"]
            )

            if import_array_temp:
                station = frappe.get_value("R400000", {"shipment_number": shipment}, "consignee_city")
                consignee_number = import_array_temp[0].consignee_number
                icris = frappe.get_list("ICRIS List",
                    filters=[
                        ["shipper_no", "=", consignee_number]
                    ],
                    fields=["shipper_name", "shipper_no"]
                )
                if icris:
                    customer = icris[0].shipper_name
                    billing_type = frappe.get_value("Customer", icris[0].shipper_name, "custom_billing_type")
                    icris_number = icris[0].shipper_no


            # Create a new shipment document
            shipment_doc = frappe.new_doc("Shipment Number")
            shipment_doc.set("shipment_number", shipment)
            shipment_doc.set("customer", customer)
            shipment_doc.set("billing_term",billing_term)
            shipment_doc.set("date_shipped", date_shipped)
            shipment_doc.set("station", station)
            shipment_doc.set("icris_number", icris_number)
            shipment_doc.set("billing_type", billing_type)
            shipment_doc.insert()
            shipment_doc.save()
            frappe.db.commit()
















def insert_data(arrays, frm, to,date_format):
    shipment_num = None
    pkg_trck = None
   
    setting = frappe.get_doc("Manifest Setting Definition")
    country_map = {j.code: j.country for j in setting.country_codes}
    replacement_map = {
        (record.field_name, record.code): record.replacement
        for record in setting.field_names_and_records
    }
    field_names_array = [record.field_names for record in setting.country_and_surcharge_codes_field_names]
    parent_doctype_map = {record.record[:2]: record.record for record in setting.doctypes_with_child_records}

    for line in arrays:
       
        doctype_name = "R" + line[frm:to].strip()
        old_doctype_name = line[frm:to].strip()
        
        
        prefix = doctype_name[:2]

       
        if prefix in parent_doctype_map:
            doctype_name = parent_doctype_map[prefix]
        
        try:
            
            definition = frappe.get_doc("Definition Manifest", doctype_name)
            for row in definition.definitions:
                if row.field_name == "shipment_number":
                    shipst = row.from_index - 1
                    shipto = row.to_index
                    shipment_num = line[shipst:shipto].strip()
                
                if row.field_name == "package_tracking_number":
                    pkg_trckt = row.from_index - 1
                    pkg_trckto = row.to_index
                    pkg_trck = line[pkg_trckt:pkg_trckto].strip()

            print(f"Looking for docs with: Shipment Num: {shipment_num}, Package Tracking: {pkg_trck}")

        except frappe.DoesNotExistError:
            continue
        
       
        if prefix in parent_doctype_map:
            for record in setting.doctypes_with_child_records:
                if doctype_name == record.record:
                    filter_str = record.filter

                    
                    if "pkg_trck" in filter_str and pkg_trck:
                        filter_str = re.sub(r'\b(pkg_trck)\b', f'"{pkg_trck}"', filter_str)
                    
                    
                    if "shipment_num" in filter_str and shipment_num:
                        filter_str = re.sub(r'\b(shipment_num)\b', f'"{shipment_num}"', filter_str)
                        
                   
                    if "old_doctype_name" in filter_str and old_doctype_name:
                        filter_str = re.sub(r'\b(old_doctype_name)\b', f'"{old_doctype_name}"', filter_str)
                    print(filter_str)
                    docs = frappe.get_list(doctype_name, filters=filter_str)



        
        else:
            docs = frappe.get_list(doctype_name, filters={'shipment_number': shipment_num})

        
        if docs:
            print("Doc found:", docs[0])
            docss = frappe.get_doc(doctype_name, docs[0])
            docss.set("check", 0)
            for child_record in definition.definitions:
                field_name = child_record.field_name
                from_index = child_record.from_index - 1
                to_index = child_record.to_index
                field_data = line[from_index:to_index].strip()

                
                if field_name in field_names_array:
                    
                    print(field_name," is present", doctype_name) 
                    if field_data in country_map:
                        field_data = country_map[field_data]


                key = (str(field_name), str(field_data)) 
                print(f"Checking key: {key}")

                if key in replacement_map:
                    field_data = replacement_map[key]
                    print(f"Replaced field data with: {field_data}")
                else:
                    print(f"Key {key} not found in replacement_map.")

                for field in setting.date_conversion_field_names:
                    if field_name == field.field_name and doctype_name == field.doctype_name:

                        try:
                            date_object = datetime.strptime(field_data, date_format)
                            output_date_format = "%Y-%m-%d"
                            field_data = date_object.strftime(output_date_format)

                        except: 
                            pass
        
                for field in setting.fields_to_divide:
                    
                    if doctype_name == field.doctype_name and field_name == field.field_name:
                        try:
                            field_data = float(field_data) if field_data else 0.0
                        except ValueError:
                            # Handle the case where field_data is not a number
                            frappe.log_error(f"Cannot convert field_data '{field_data}' to float", "Conversion Error")
                            field_data = 0.0
                        if field.number_divide_with:
                            field_data = field_data / field.number_divide_with
                        # print(field_data , field_name,"NEW")
                docss.set(field_name, field_data)
            docss.save()
            frappe.db.commit()
            print(doctype_name, shipment_num, "Updating")
        else:
            
            doc = frappe.new_doc(doctype_name)
            for child_record in definition.definitions:
                field_name = child_record.field_name
                from_index = child_record.from_index - 1
                to_index = child_record.to_index
                field_data = line[from_index:to_index].strip()


                if field_name in field_names_array:
                    if field_data in country_map:
                        field_data = country_map[field_data]


                key = (field_name, field_data)
                if key in replacement_map:
                    field_data = replacement_map[key]

                for field in setting.date_conversion_field_names:
                    if field_name == field.field_name and doctype_name == field.doctype_name:
                        try:
                            date_object = datetime.strptime(field_data, date_format)
                            output_date_format = "%Y-%m-%d"
                            field_data = date_object.strftime(output_date_format)
                        except:
                            pass
                # doc.set(field_name, field_data)
                for field in setting.fields_to_divide:
                    
                    if doctype_name == field.doctype_name and field_name == field.field_name:
                        try:
                            field_data = float(field_data) if field_data else 0.0
                        except ValueError:
                            # Handle the case where field_data is not a number
                            frappe.log_error(f"Cannot convert field_data '{field_data}' to float", "Conversion Error")
                            field_data = 0.0
                        if field.number_divide_with:
                            field_data = field_data / field.number_divide_with
                doc.set(field_name, field_data)

            print(doctype_name, shipment_num, "Inserting")
            doc.insert()
            doc.save()



def modified_manifest_update(main_doc,arrays2,pkg_from,pkg_to):
    setting = frappe.get_doc("Manifest Setting Definition")
    
    for line in arrays2:
        # pkg_trck = line[pkg_from:pkg_to].strip()
        pkg_trck = "49455852868"
        print("pkg_trck",pkg_trck,"\n\n")
        docl = frappe.get_list(main_doc.record_to_modify, filters={"package_tracking_number": pkg_trck })
        if docl:
            doc = frappe.get_doc(main_doc.record_to_modify , docl[0])
            for child in setting.definition:
                field_name = child.field_name
                from_index = child.from_index - 1
                to_index = child.to_index
                field_data = line[from_index:to_index].strip()
                doc.set(field_name,field_data)
                print(field_name , "  ",field_data)
            doc.save()
        else:
            frappe.get_doc({
                                            "doctype": "Error Log",
                                            "method": "Package tracking Number not found",
                                            "error": f"""Package tracking Number:,{pkg_trck}"""
    
                                        }).insert()





    

class ManifestUploadData(Document):
    def on_submit(self):
       
        if self.attach_file:
            
           
            file_name = frappe.db.get_value("File", {"file_url": self.attach_file}, "name")
           
            file_doc = frappe.get_doc("File", file_name)
            content = file_doc.get_content()
            arrays = content.split('\n')
            frm = int(self.from_index)-1
            to = int(self.to_index)
            shipfrom = int(self.shipment_number_from_index)-1
            shipto = int(self.shipment_number_to_index)
            chunk_size = 10  
            current_index = 0 
            
            while current_index < len(arrays):
                chunk = arrays[current_index:current_index + chunk_size]             
                current_index += chunk_size
                enqueue(insert_data, arrays=chunk,frm=frm, to=to, date_format = self.date_format, queue="default")
            enqueue(storing_shipment_number,arrays=arrays, frm=shipfrom, to=shipto, doc=self.name ,queue="default")



        if self.manifest_modification_process and self.modified_file:

            file_name2 = frappe.db.get_value("File", {"file_url": self.modified_file}, "name")
            file_doc2 = frappe.get_doc("File", file_name2)
            content2 = file_doc2.get_content()
            arrays2 = content2.split('\n')
            pkg_from = int(self.package_tracking_from_index)-1
            pkg_to = int(self.package_tracking_to_index)-1
            chunk2_size = 10
            current2_index = 0

            while current2_index < len(arrays2):
                chunk2 = arrays2[current2_index:current2_index + chunk2_size]
                current2_index += chunk2_size
                # modified_manifest_update(main_doc = self, arrays2 = chunk2, pkg_from = pkg_from , pkg_to= pkg_to)
                enqueue(modified_manifest_update,main_doc = self, arrays2 = chunk2, pkg_from = pkg_from , pkg_to= pkg_to,  queue = "default")
                    
                
            