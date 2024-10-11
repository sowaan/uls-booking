from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import getdate
import json
import re


def generate_sales_invoice_enqued(doc_str):

    try:
       
        doc = json.loads(doc_str)
        final_rate = 0
        tarif = 0
        discounted_amount = 0
        selling_rate_zone = None
        selling_rate_country = 0
        arrayy=[]
        try:
            definition = frappe.get_doc("Sales Invocie Def", "54mcf25ihm")
        except frappe.DoesNotExistError:
            frappe.throw(frappe._("Sales Invoice Definition with ID '54mcf25ihm' does not exist"))
        except frappe.PermissionError:
            frappe.throw(frappe._("You do not have permission to access the Sales Invoice Definition"))
        except Exception as e:
            frappe.throw(frappe._("Error fetching Sales Invoice Definition: ") + str(e))

      
        shipment = doc.get("shipment_numbers", "")
        shipments = [value.strip() for value in shipment.split(",") if value.strip()]
        setting = frappe.get_doc("Manifest Setting Definition")
        excluded_codes = []
        included_codes=[]
    


        for code in setting.surcharges_code_excl_and_incl:

            excluded_codes.append(code.excluded_codes)
            included_codes.append(code.included_codes)

        for shipment in shipments:
            final_rate = 0
            tarif = 0
            signal = 0
            customer_signal =0
            final_discount_percentage = 0
          
            checkship = frappe.get_list("Sales Invoice",
                                        filters = {"custom_shipment_number":shipment})
            if checkship:
                continue
            
            sales_invoice = frappe.new_doc("Sales Invoice")
            sales_invoice.customer = "UPS SCS PAKISTAN PVT LTD ( B )"
            
           
            doctype_name =0
            total_charges_incl_fuel = 0
            total_charges_other_charges = 0
            FSCcharges = 0
            FSCpercentage = 0
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
                   
            
            icris_number = None
            selling_group = None
            selling_rate = None
            
            if sales_invoice.custom_shipper_country == "PAKISTAN":
                imp_exp = "Export"
                icris_number = sales_invoice.custom_shipper_number

            else:
                imp_exp = "Import"
                icris_number = sales_invoice.custom_consignee_number


            try:
                icris_account = frappe.get_doc("ICRIS Account", icris_number)
                # print(icris_account)
            except frappe.DoesNotExistError:
                
                print("ICRIS Account does not exist. and the Icris number is :" , icris_number , "The shipment Number :", sales_invoice.custom_shipment_number,"\n \n")
                continue            
            except Exception as e:
                print(f"An error occurred: {str(e)}")
            
            
            





            
            if sales_invoice.custom_billing_term in ["F/D","P/P"] and sales_invoice.custom_shipper_country == "PAKISTAN":
                check1 = frappe.get_list("ICRIS List",
                                        filters = {"shipper_no":sales_invoice.custom_shipper_number})
                
                if check1:
                  
                    icris = frappe.get_doc("ICRIS List",check1[0].name)
                    
                    sales_invoice.customer = icris.shipper_name
                    
                   
                    tt = frappe.get_doc("Territory", {"name": sales_invoice.custom_shipper_city})
                    pt = tt.parent_territory
                    if pt != "All Territories":
                        stc = frappe.get_doc("Sales Taxes and Charges Template", {"province": pt})
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
                            # else:
                                
                    
                    if selling_group:
                        
                        zones = frappe.get_list("Zone",
                                                filters = {"country" : origin_country , "is_single_country":1})
                        
                        flag = 0
                        if zones:
                                                     
                            selling_rate_name = frappe.get_list("Selling Rate",
                                filters={
                                    "country": origin_country,
                                    "service_type": service_type[0].get("name"),
                                    "package_type": sales_invoice.custom_shipment_type,
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
                                    selling_rate_name = frappe.get_list("Selling Rate",
                                        filters={
                                            "zone": zone_with_out_country,
                                            "service_type": service_type[0].get("name"),
                                            "package_type": sales_invoice.custom_shipment_type,
                                            "rate_group": selling_group 
                                        }
                                    )
                                
                                    
                                    if selling_rate_name:        
                                        selling_rate_zone = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                        selling_rate = selling_rate_zone
                                        
                                    else :
                                    
                                        print("No Selling Rate Found The shipment nummber is :" ,sales_invoice.shipment_number , "Zone:", zone_with_out_country , "Service Type :" ,  service_type[0].get("name") , "Package type :",sales_invoice.shipment_type , "Selling Group :", selling_group ,"Icris Number :", icris_number,"\n \n")
                                        continue
                            else:
                                continue            
                        
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        # print(" Selling Group :" ,selling_group,"service type:",service_type , "and the psoting date is ", posting_date, "Icris Number :", icris_number , "Selling Rate:",selling_rate , "Origin Country:",origin_country)       
                        print("Selling Group:",selling_group , "Service Type:",service_type[0].get("name"),"Package TYpe :",sales_invoice.custom_shipment_type,"Zone:",origin_country,zone_with_out_country,"Shipment NUmber:",shipment,"Icris Number:",icris_number)
                        

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
                    else:
                        print("No selling Group Found","Service Type:",service_type[0].get("name"),"Package TYpe :",sales_invoice.custom_shipment_type,"Zone:",origin_country,zone_with_out_country,"Shipment NUmber:",shipment,"Icris Number:",icris_number)   
                    



            elif sales_invoice.custom_billing_term == "F/C" and sales_invoice.custom_shipper_country != "PAKISTAN":
               
                
                check = frappe.get_list("ICRIS List",
                                        filters = {"shipper_no":sales_invoice.custom_consignee_number})
                if check:
                    icris1 = frappe.get_doc("ICRIS List", {"shipper_no": check[0].name})
                   
                    sales_invoice.customer = icris1.shipper_name
                    
                    mm = frappe.get_doc("Territory", {"name": sales_invoice.custom_consignee_city})
                    vv = mm.parent_territory
                    
                    if vv != "All Territories":
                        bb = frappe.get_doc("Sales Taxes and Charges Template", {"province": vv})
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
                           

                    if selling_group:
                        
                        zones = frappe.get_list("Zone",
                                                filters = {"country" : origin_country , "is_single_country":1})
                        
                        flag = 0
                        if zones:
                                                     
                            selling_rate_name = frappe.get_list("Selling Rate",
                                filters={
                                    "country": origin_country,
                                    "service_type": service_type[0].get("name"),
                                    "package_type": sales_invoice.custom_shipment_type,
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
                                    selling_rate_name = frappe.get_list("Selling Rate",
                                        filters={
                                            "zone": zone_with_out_country,
                                            "service_type": service_type[0].get("name"),
                                            "package_type": sales_invoice.custom_shipment_type,
                                            "rate_group": selling_group 
                                        }
                                    )
                                
                                    
                                    if selling_rate_name:        
                                        selling_rate_zone = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                        selling_rate = selling_rate_zone
                                        
                                    else :
                                    
                                        print("No Selling Rate Found The shipment nummber is :" ,sales_invoice.shipment_number , "Zone:", zone_with_out_country , "Service Type :" ,  service_type[0].get("name") , "Package type :",sales_invoice.shipment_type , "Selling Group :", selling_group ,"Icris Number :", icris_number,"\n \n")
                                        continue
                            else:
                                continue            
                        
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        # print(" Selling Group :" ,selling_group,"service type:",service_type , "and the psoting date is ", posting_date, "Icris Number :", icris_number , "Selling Rate:",selling_rate , "Origin Country:",origin_country)       
                        print("Selling Group:",selling_group , "Service Type:",service_type[0].get("name"),"Package TYpe :",sales_invoice.custom_shipment_type,"Zone:",origin_country,zone_with_out_country,"Shipment NUmber:",shipment,"Icris Number:",icris_number)
                        

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
                    else:
                        print("No selling Group Found","Service Type:",service_type[0].get("name"),"Package TYpe :",sales_invoice.custom_shipment_type,"Zone:",origin_country,zone_with_out_country,"Shipment NUmber:",shipment,"Icris Number:",icris_number) 
           
            
            
            
            
            
            
            
            
            
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

                
                sales_invoice.surcharges_and_amounts = []
                total_charges_incl_fuel = sum(amounts_incl_fuel)
                total_charges_other_charges = sum(amounts_other_charges)
                for surcharge_code, code, amount in zip(surcharge_codes_other_charges, codes_other_charges, amounts_other_charges):
                    if code: 
                        sales_invoice.append("surcharges_and_amounts", {
                            "surcharge": surcharge_code, 
                            "code": code,                
                            "amount": amount             
                        })

               
                sales_invoice.surcharges_and_amounts_incl_fuel = []

                for surcharge_code, code, amount in zip(surcharge_codes_incl_fuel, codes_incl_fuel, amounts_incl_fuel):
                    if code: 
                        sales_invoice.append("surcharges_and_amounts_incl_fuel", {
                            "surcharge": surcharge_code,  
                            "code": code,                
                            "amount": amount            
                        })
                
                sales_invoice.total_surcharges_excl_fuel_charges = total_charges_other_charges
                sales_invoice.total_surcharges_incl_fuel_charges = total_charges_incl_fuel
                FSCpercentage = frappe.db.get_value('Additional Charges', 'Fuel Surcharge', 'percentage')
                if FSCpercentage and tarif:
                        FSCcharges = (total_charges_incl_fuel + final_rate) * (FSCpercentage / 100 )
                        # print(FSCcharges)
                        
                print("Tarif :" , tarif , "Final Rate :", final_rate , "Percentage" , final_discount_percentage ,"Selling Rate :", selling_rate , "Additional Charges Percentage:",FSCpercentage , "Fuel INCL :",total_charges_incl_fuel , "FSC CHARGES" ,FSCcharges  )

            shipmentbillingcheck = 0
            shipmentbillingamount = 0
            if sales_invoice.customer:
                shipmentbillingcheck = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipping_bill_charges_applicable')
                if shipmentbillingcheck:
                    if imp_exp == "Export":
                        shipmentbillingamount = frappe.db.get_value('Additional Charges', 'Shipping Bill Charges', 'export_amount')
                        
                    elif imp_exp == "Import":
                        shipmentbillingamount = frappe.db.get_value('Additional Charges', 'Shipping Bill Charges', 'import_amount')
                        
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
            


            if sales_invoice.customer != "UPS SCS PAKISTAN PVT LTD ( B )":
                if decalred_value > 0:
                    
                    percent = frappe.db.get_value('Additional Charges', 'Declare Value', 'percentage')
                    minimum_amount = frappe.db.get_value('Additional Charges', 'Declare Value', 'minimum_amount')
                    result = decalred_value * (percent / 100)
                    max_insured = max(result , minimum_amount)
                    # print(max_insured , " ", percent , " ", minimum_amount, " ", decalred_value)
                    if max_insured > 0 and sales_invoice.custom_shipment_type == "NON-DOCUMENTS":
                        rows = {'item_code': "INS", 'qty': '1', 'rate': max_insured}
                        print("INS")
                        sales_invoice.append('items', rows)

                
                sales_invoice.discount_amount = tarif - final_rate
                sales_invoice.custom_selling_percentage = final_discount_percentage


                if total_charges_other_charges:
                    rows = {'item_code': setting.other_charges, 'qty': 1} 
                    print("OC")
                    sales_invoice.append('items', rows)
                if FSCcharges:
                    rows = {'item_code': setting.fuel_charges, 'qty': '1', 'rate': FSCcharges}
                    print("FSC")
                    sales_invoice.append('items', rows)
                if tarif:
                    rows = {'item_code' : setting.freight_charges , 'qty' : '1' , 'rate' : tarif}
                    print("EX")
                    sales_invoice.append('items' , rows)
                if shipmentbillingamount:
                    rows = {'item_code' : setting.shipment_billing_charges , 'qty' : '1' , 'rate' : shipmentbillingamount}
                    print("SBC")
                    sales_invoice.append('items' , rows)



                    
            export_compensation_amount = 0
            
                
            # print(sales_invoice.currency)
            
            if sales_invoice.customer == "UPS SCS PAKISTAN PVT LTD ( B )":
                sig = 0
                for comp in definition.compensation_table:
                    if sales_invoice.custom_billing_term == comp.shipment_billing_term and sales_invoice.custom_shipment_type == comp.shipping_billing_type and imp_exp == comp.case:
                        export_compensation_amount = comp.document_amount
                        # print(sales_invoice.billing_term_field," ",sales_invoice.shipment_type," ",imp_exp," ",export_compensation_amount)
                        rows = {'item_code': "CC", 'qty': '1', 'rate': export_compensation_amount}
                        sales_invoice.append('items', rows)
                        sig = 1
                        break
                    
                if sig == 0:
                    arrayy.append(sales_invoice.custom_shipper_number)
                    print("Shipper Number : ",sales_invoice.custom_shipper_number, " not Found in the Icris", "Shipment Number :", shipment)
                    continue
                    # print(sales_invoice.billing_term_field," ",sales_invoice.shipment_type," ",imp_exp," ",import_compensation_amount + "Sufyan")
                    rows = {'item_code': "CC", 'qty': '1', 'rate': 0}
                    sales_invoice.append('items', rows)
                    print("The Customer is UPS and the Shipment number is :", sales_invoice.custom_shipment_number,"\n \n")
            if not sales_invoice.items:
                print("shipment number" , sales_invoice.custom_shipment_number , "Item table is empty, so cannot make Sales Invoice. \n \n \n")
                continue
            # sales_invoice.validate()
            # sales_invoice.check_conversion_rate()
            
            
            sales_invoice.insert()
            sales_invoice.save()
            if sales_invoice.customer != "UPS SCS PAKISTAN PVT LTD ( B )":
                for row in sales_invoice.items:
                    if row.item_code == "OC":
                    
                        frappe.db.set_value(row.doctype , row.name ,"rate" , total_charges_other_charges )
                        frappe.db.set_value(row.doctype , row.name ,"amount" , total_charges_other_charges )
                        frappe.db.set_value(row.doctype , row.name ,"base_amount" , total_charges_other_charges )
                        frappe.db.set_value(row.doctype , row.name ,"base_rate" , total_charges_other_charges )
                frappe.db.set_value(sales_invoice.doctype , sales_invoice.name ,"total" , total_charges_other_charges +  FSCcharges + tarif + max_insured + shipmentbillingamount )
                frappe.db.set_value(sales_invoice.doctype , sales_invoice.name ,"grand_total" , total_charges_other_charges +  FSCcharges + tarif + max_insured + shipmentbillingamount)
        
               



    except json.JSONDecodeError:
        frappe.throw(frappe._("Invalid JSON data"))
    except Exception as e:
        frappe.throw(frappe._("An error occurred: ") + str(e))

@frappe.whitelist()
def generate_sales_invoice(doc_str):
    generate_sales_invoice_enqued(doc_str)
    # enqueue(generate_sales_invoice_enqued, doc_str=doc_str, queue="default")
    # generate_sales_invoice(doc_str)
   




















def storing_shipment_number(arrays, frm, to, doc):
    shipment_numbers = set() 

    for line in arrays:
        try:
            shipment_num = line[frm:to].strip()
            if shipment_num: 
                shipment_numbers.add(shipment_num) 
        except IndexError:
            frappe.log_error(f"IndexError processing line: {line}", "Data Processing Error")
            continue
        except Exception as e:
            frappe.log_error(f"Unexpected error processing line: {line}. Error: {str(e)}", "Data Processing Error")
            continue

    shipment_numbers_str = ', '.join(shipment_numbers) 
    value = len(shipment_numbers)

    try:
        doc1 = frappe.get_doc("Manifest Upload Data", doc)
        doc1.shipment_numbers = shipment_numbers_str
        doc1.total_no_of_shipment_numbers = value  
        doc1.save() 
        frappe.db.commit()
    except frappe.DoesNotExistError:
        frappe.log_error(f"Document {doc} does not exist.", "Document Retrieval Error")
    except Exception as e:
        frappe.log_error(f"Error saving document {doc}: {str(e)}", "Document Save Error")
        raise

    frappe.db.commit()














def insert_data(arrays, frm, to):
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
        old_doctype_name = doctype_name
        
        
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


                doc.set(field_name, field_data)

            print(doctype_name, shipment_num, "Inserting")
            doc.insert()
            doc.save()
            

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
            
            
            storing_shipment_number(arrays=arrays, frm=shipfrom, to=shipto, doc=self.name)
           
            while current_index < len(arrays):
                
                chunk = arrays[current_index:current_index + chunk_size]                
                
                current_index += chunk_size
                insert_data(chunk,frm,to )
                
            
         