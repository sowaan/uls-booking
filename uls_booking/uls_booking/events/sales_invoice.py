from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import getdate
import json
import re
from datetime import datetime
from frappe import _
import logging


def generate_invoice( self, method):
    sales_invoice = self
    if sales_invoice.custom_duty_and_taxes_invoice != 1 :
        shipment_number = sales_invoice.custom_shipment_number
        already_present = 0
        log_list = frappe.get_list("Sales Invoice Logs",filters ={"shipment_number":shipment_number})
        if log_list:
            already_present = 1
            log_doc = frappe.get_doc("Sales Invoice Logs",log_list[0].name)
        else:
            log_doc = frappe.new_doc("Sales Invoice Logs")
        logs = []
        final_rate = 0
        tarif = 0
        discounted_amount = 0
        selling_rate_zone = None
        selling_rate_country = 0
        arrayy=[]
        sales_name= []
        full_tariff = None
        definition = frappe.get_doc("Sales Invoice Definition", sales_invoice.custom_sales_invoice_definition)
        setting = frappe.get_doc("Manifest Setting Definition")
        if sales_invoice.taxes_and_charges:
            sales_invoice.taxes_and_charges= None
            sales_invoice.taxes = []
        sales_invoice.items = []
        sbc_included= []
        sbc_excluded = []
        for code in setting.sbc_charges_package_types:
            sbc_included.append(code.sales_invoice_package_type)
            sbc_excluded.append(code.excluded_package_types_in_sales_invoice)
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
        total_invoices = 0
        actual_invoices = 0
        
        
        discounted_amount = discounted_amount +1
        final_rate = 0
        tarif = 0
        signal = 0
        final_discount_percentage = 0
        selected_weight = 0
        origin_country = None
        
        
        company = definition.default_company
        customer = frappe.get_doc("Company",company)

        # frappe.msgprint(str(customer.custom_default_customer))
        # sales_invoice.customer = None
        # sales_invoice.customer = customer.custom_default_customer
        # sales_invoice.set("customer", customer.custom_default_customer)
        end_date = sales_invoice.posting_date
        doctype_name =0
        total_charges_incl_fuel = 0
        total_charges_other_charges = 0
        FSCcharges = 0
        FSCpercentage = 0
        latest_valid_percentage = 0
        shipment_type = 0
        date2 = getdate(end_date)
        sales_invoice.posting_date = date2
        posting_date = getdate(sales_invoice.posting_date)
        sales_invoice.set_posting_time = 1
        exempt_customer = 0



        icris_number = None
        selling_group = None
        selling_rate = None
        shipped_date = getdate(sales_invoice.custom_date_shipped)
        print(shipped_date)
       
        exchange_rate = frappe.get_list(
            "Currency Exchange",
            filters={"from_currency": "USD", "to_currency": "PKR", "date": shipped_date},
            fields=["name", "exchange_rate", "date"],
            order_by="date desc",
            limit_page_length=1
        )
        if not exchange_rate:
            exchange_rate = frappe.get_list(
                "Currency Exchange",
                filters={"from_currency": "USD", "to_currency": "PKR", "date": [">", shipped_date]},
                fields=["name", "exchange_rate", "date"],
                order_by="date asc",  # Get the earliest available future exchange rate
                limit_page_length=1
            )

        
        if not exchange_rate:
            exchange_rate = frappe.get_list(
                "Currency Exchange",
                filters={"from_currency": "USD", "to_currency": "PKR", "date": ["<", shipped_date]},
                fields=["name", "exchange_rate", "date"],
                order_by="date desc",  # Get the closest previous exchange rate
                limit_page_length=1
            )
        if exchange_rate:
            print(exchange_rate[0].exchange_rate)
            sales_invoice.conversion_rate = exchange_rate[0].exchange_rate

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
            
        if sales_invoice.custom_package_type:
            shipment_type = sales_invoice.custom_package_type
        else:
            shipment_type = sales_invoice.custom_shipment_type
            
        try:
            icris_account = frappe.get_doc("ICRIS Account", icris_number)
        
        except frappe.DoesNotExistError:
            logs.append(f"No icris Account Found {icris_number}")
            print("No icris Account Found")
            if definition.unassigned_icris_number:
                icris_account = frappe.get_doc("ICRIS Account", definition.unassigned_icris_number)
        print(shipment_type)


        if sales_invoice.custom_billing_term in export_billing_term and sales_invoice.custom_shipper_country == definition.origin_country.upper():
            check1 = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
            if not check1:
                logs.append(f"No ICRIS Account Found {icris_number}")
                print("No ICRIS Account Found")
                icris_number = definition.unassigned_icris_number
            if icris_number:
                icris_doc = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
                icris = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                if icris.shipper_name:
                    sales_invoice.customer = icris.shipper_name
                    customer_name = frappe.db.get_value("Customer", sales_invoice.customer, 'customer_name')
                    sales_invoice.customer_name = customer_name
                else:
                    logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}")
                    print("No Customer Found")
                exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
                tax_rule = None
                tax_rule_name = None
                tax_flag = 0
                if exempt_customer == 0:
                    tt = frappe.get_doc("Territory", {"name": sales_invoice.custom_shipper_city})
                    print(tt.name)
                    if tt:
                        pt = tt.parent_territory
                        print(pt)
                        if pt != "All Territories":
                            stc = frappe.get_doc("Sales Taxes and Charges Template", {"custom_province": pt})

                            if stc:
                                # Fetch Tax Rule
                                tax_rule = frappe.get_list(
                                    "Tax Rule",
                                    filters={
                                        "sales_tax_template": stc.name,
                                        "from_date": ["<=", shipped_date],
                                        "to_date": [">=", shipped_date]
                                    }
                                )
                                if tax_rule:
                                    tax_rule_name = tax_rule[0].name
                                if tax_rule_name:
                                    sales_invoice.set("taxes_and_charges", stc.name)

                                    for sale in stc.taxes:
                                        rows = {
                                            'charge_type': sale.charge_type,
                                            'description': sale.description,
                                            'account_head': sale.account_head,
                                            'cost_center': sale.cost_center,
                                            'rate': sale.rate,
                                            'account_currency': sale.account_currency
                                        }
                                        sales_invoice.append('taxes', rows)
                                else:
                                    stc = frappe.get_doc("Sales Taxes and Charges Template", definition.default_sales_tax)
                                    if stc:
                                        sales_invoice.set("taxes_and_charges", stc.name)
                                        for sale in stc.taxes:
                                            rows = {
                                                'charge_type': sale.charge_type,
                                                'description': sale.description,
                                                'account_head': sale.account_head,
                                                'cost_center': sale.cost_center,
                                                'rate': sale.rate,
                                                'account_currency': sale.account_currency
                                            }
                                            sales_invoice.append('taxes', rows)

                                        logs.append(f"No Territory Found {sales_invoice.custom_shipper_city} so Using default Tax")
                                        print("No Territory Found so Using default Tax")
                    else:
                        stc = frappe.get_doc("Sales Taxes and Charges Template", definition.default_sales_tax)
                        if stc:
                            sales_invoice.set("taxes_and_charges", stc.name)
                            for sale in stc.taxes:
                                rows = {
                                    'charge_type': sale.charge_type,
                                    'description': sale.description,
                                    'account_head': sale.account_head,
                                    'cost_center': sale.cost_center,
                                    'rate': sale.rate,
                                    'account_currency': sale.account_currency
                                }
                                sales_invoice.append('taxes', rows)

                            logs.append(f"No Territory Found {sales_invoice.custom_shipper_city} so Using default Tax")
                            print("No Territory Found so Using default Tax")

                
                if sales_invoice.custom_consignee_country:
                    origin_country = sales_invoice.custom_consignee_country
                    origin_country = origin_country.capitalize()
                    
                zone_with_out_country = None
                selling_rate_name = None
                
                service_type = frappe.get_list("Service Type",
                                    filters = {"imp__exp":imp_exp , "service": sales_invoice.custom_service_type})
                if service_type:
                    for icris in icris_account.rate_group:

                        if  icris.service_type == service_type[0].get("name")  and icris.from_date <= shipped_date and shipped_date <= icris.to_date :
                            selling_group = icris.rate_group
                            break
                        
                    if not selling_group:
                        logs.append(f"No selling group Found thats why using Default Selling group")
                        print("No selling group Found thats why using Default Selling group")
                        selling_group = definition.default_selling_group 
                full_tariff_flag = 0
                
                print(selling_group , " = ", definition.default_selling_group)



                if selling_group == definition.default_selling_group:
                    # Look for Full Tariff
                    zones = frappe.get_list("Zone",
                                            filters = {"country" : origin_country , "is_single_country":1})
                    flag = 0
                    
                    if zones:
                        sales_invoice.custom_zone = zones[0].name
                        print("Zone with Country:", zones[0].name)

                        full_tariff_query = """
                            SELECT name
                            FROM `tabFull Tariff`
                            WHERE country = %s
                            AND service_type = %s
                            AND package_type = %s
                            AND valid_from <= %s
                            AND expiry_date >= %s
                        """
                        params = (origin_country, service_type[0].get("name"), shipment_type, shipped_date, shipped_date)
                        full_tariff_name = frappe.db.sql(full_tariff_query, params, as_dict=True)

                        if full_tariff_name:
                            full_tariff = frappe.get_doc("Full Tariff", full_tariff_name[0]["name"])
                            full_tariff_flag = 1

                        else:
                            flag = 1  # No Full Tariff found

                    elif not zones:
                        flag = 1  # No country-based zones found

                    # If no Full Tariff found, try finding it by region
                    if flag == 1:
                        try:
                            countries = frappe.db.get_all("Country Names", filters={"countries":origin_country} , fields = ['parent'])
                            
                            if countries:
                                zone_with_out_country = countries[0].parent
                                if zone_with_out_country:
                                    sales_invoice.custom_zone = zone_with_out_country

                                    full_tariff_query = """
                                        SELECT name
                                        FROM `tabFull Tariff`
                                        WHERE zone = %s
                                        AND service_type = %s
                                        AND package_type = %s
                                        AND valid_from <= %s
                                        AND expiry_date >= %s
                                    """
                                    params = (zone_with_out_country, service_type[0].get("name"), shipment_type, shipped_date, shipped_date)
                                    full_tariff_name = frappe.db.sql(full_tariff_query, params, as_dict=True)

                                    if full_tariff_name:
                                        full_tariff = frappe.get_doc("Full Tariff", full_tariff_name[0]["name"])
                                        full_tariff_flag = 1

                        except:
                            logs.append("No Full Tariff Found. Using Default Tariff")
                            print("No Full Tariff Found. Using Default Tariff")

                    # **Calculate Rate if Full Tariff is Found**
                    if full_tariff:
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        flg = 0
                        last_row = {}

                        for row in full_tariff.package_rate:
                            if my_weight <= row.weight:
                                final_rate = row.rate
                                flg = 1
                                break
                            else:
                                last_row = row

                        if flg == 0:
                            final_rate = (last_row.rate / last_row.weight) * my_weight
                            final_discount_percentage = 0.00
                        tarif = final_rate / (1- (final_discount_percentage/100))
                        print(final_rate)
                        
                        

                        print(f"Final Rate from Full Tariff: {tarif}")

                    else:
                        # **If Full Tariff is NOT found, switch to Selling Rate Logic**
                        print("Full Tariff Not Found, Switching to Selling Rate Logic")




                if selling_group and full_tariff_flag == 0:

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
                            print(selling_rate)
                            
                        else :
                            flag = 1
                        
                    elif not zones:
                        flag = 1

                    if flag == 1:
                        try:
                            countries = frappe.db.get_all("Country Names", filters={"countries":origin_country} , fields = ['parent'])
                            
                            if countries:
                                zone_with_out_country = countries[0].parent
                                if zone_with_out_country:
                                    sales_invoice.custom_zone = zone_with_out_country
                                    selling_rate_name = frappe.get_list("Selling Rate",
                                        filters={
                                            "zone": countries[0].parent,
                                            "service_type": service_type[0].get("name"),
                                            "package_type": shipment_type,
                                            "rate_group": selling_group 
                                        }
                                    )
                                
                                    if selling_rate_name:        
                                        selling_rate = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                        print(selling_rate)
                                        
                                    else :
                                        logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                        print("No Selling Rate Found Thats why using Default Selling Rate")
                                        if definition.default_selling_rate:
                                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                                            print(selling_rate)
                            else:
                                logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                print("No Selling Rate Found Thats Why using Default Selling Rate")
                                if definition.default_selling_rate:
                                    selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)    
                                    print(selling_rate)          
                        except:
                            logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                            print("No Selling Rate Found Thats why using Default Selling Rate")
                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                            print("Selling Rate",selling_rate)
                            
                    
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
                        print(final_rate)



            
        elif sales_invoice.custom_billing_term in import_billing_term and sales_invoice.custom_shipper_country != definition.origin_country.upper():
            check = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
            if not check:
                logs.append(f"No ICRIS Account Found {icris_number}")
                print("No ICRIS Account Found Thats Why using Default Icris")
                icris_number = definition.unassigned_icris_number
            if icris_number:
                icris_doc = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
                icris1 = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                
                if icris1.shipper_name:
                    sales_invoice.customer = icris1.shipper_name
                    customer_name = frappe.db.get_value("Customer", sales_invoice.customer, 'customer_name')
                    sales_invoice.customer_name = customer_name
                else:
                    logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}") 
                    print("No Customer Found")
                exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
                tax_rule = None
                tax_rule_name = None
                tax_flag = 0
                if exempt_customer == 0:
                    mm = frappe.get_doc("Territory", {"name": sales_invoice.custom_consignee_city})
                    if mm:
                        vv = mm.parent_territory
                        if vv != "All Territories":
                            bb = frappe.get_doc("Sales Taxes and Charges Template", {"custom_province": vv})
                            if bb:
                                tax_rule = frappe.get_list(
                                    "Tax Rule",
                                    filters={
                                        "sales_tax_template": bb.name,
                                        "from_date": ["<=", shipped_date],
                                        "to_date": [">=", shipped_date]
                                    }
                                )
                                if tax_rule:
                                    tax_rule_name = tax_rule[0].name
                                if tax_rule_name:
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
                                else:
                                    stc = frappe.get_doc("Sales Taxes and Charges Template", definition.default_sales_tax)
                                    sales_invoice.set("taxes_and_charges", stc.name)
                                    for sale in stc.taxes:
                                        charge_type = sale.charge_type
                                        description = sale.description
                                        account_head = sale.account_head
                                        cost_center = sale.cost_center
                                        rate = sale.rate
                                        account_currency = sale.account_currency
                                    rows = {'charge_type': charge_type, 'description': description, 'account_head': account_head, 'cost_center':cost_center, 'rate':rate, 'account_currency':account_currency}
                                    sales_invoice.append('taxes', rows)
                                    logs.append(f"No Territory Found {sales_invoice.custom_consignee_city} so Using default Tax")
                                    print("No Territory Found Thats Why using Default Sales Tax and Template")

                    else:
                        stc = frappe.get_doc("Sales Taxes and Charges Template", definition.default_sales_tax)
                        sales_invoice.set("taxes_and_charges", stc.name)
                        for sale in stc.taxes:
                            charge_type = sale.charge_type
                            description = sale.description
                            account_head = sale.account_head
                            cost_center = sale.cost_center
                            rate = sale.rate
                            account_currency = sale.account_currency
                        rows = {'charge_type': charge_type, 'description': description, 'account_head': account_head, 'cost_center':cost_center, 'rate':rate, 'account_currency':account_currency}
                        sales_invoice.append('taxes', rows)
                        logs.append(f"No Territory Found {sales_invoice.custom_consignee_city} so Using default Tax")
                        print("No Territory Found Thats Why using Default Sales Tax and Template")
                    
                if sales_invoice.custom_shipper_country:
                    origin_country = sales_invoice.custom_shipper_country
                    origin_country = origin_country.capitalize()
                zone_with_out_country = None
                selling_rate_name = None
                service_type = frappe.get_list("Service Type",
                                    filters = {"imp__exp":imp_exp , "service": sales_invoice.custom_service_type})
                
                if service_type:
                    for icris in icris_account.rate_group:
                        if  icris.service_type == service_type[0].get("name")  and icris.from_date <= shipped_date <= icris.to_date:
                            selling_group = icris.rate_group
                            break
                if not selling_group:
                    logs.append(f"No selling group Found thats why using Default Selling group")
                    print("No Selling Group Found Thats why using Default Selling Group")
                    selling_group = definition.default_selling_group
                full_tariff_flag = 0
                
                print(selling_group , " = ", definition.default_selling_group)



                if selling_group == definition.default_selling_group:
                    # Look for Full Tariff
                    zones = frappe.get_list("Zone", filters={"country": origin_country, "is_single_country": 1})
                    flag = 0
                    
                    if zones:
                        sales_invoice.custom_zone = zones[0].name
                        print("Zone with Country:", zones[0].name)

                        full_tariff_query = """
                            SELECT name
                            FROM `tabFull Tariff`
                            WHERE country = %s
                            AND service_type = %s
                            AND package_type = %s
                            AND valid_from <= %s
                            AND expiry_date >= %s
                        """
                        params = (origin_country, service_type[0].get("name"), shipment_type, shipped_date, shipped_date)
                        full_tariff_name = frappe.db.sql(full_tariff_query, params, as_dict=True)

                        if full_tariff_name:
                            full_tariff = frappe.get_doc("Full Tariff", full_tariff_name[0]["name"])
                            full_tariff_flag = 1
                        else:
                            flag = 1  # No Full Tariff found

                    else:
                        flag = 1  # No country-based zones found

                    # If no Full Tariff found, try finding it by region
                    if flag == 1:
                        try:
                            countries = frappe.db.get_all("Country Names", filters={"countries": origin_country}, fields=['parent'])
                            
                            if countries:
                                zone_with_out_country = countries[0].parent
                                if zone_with_out_country:
                                    sales_invoice.custom_zone = zone_with_out_country

                                    full_tariff_query = """
                                        SELECT name
                                        FROM `tabFull Tariff`
                                        WHERE zone = %s
                                        AND service_type = %s
                                        AND package_type = %s
                                        AND valid_from <= %s
                                        AND expiry_date >= %s
                                    """
                                    params = (zone_with_out_country, service_type[0].get("name"), shipment_type, shipped_date, shipped_date)
                                    full_tariff_name = frappe.db.sql(full_tariff_query, params, as_dict=True)

                                    if full_tariff_name:
                                        full_tariff = frappe.get_doc("Full Tariff", full_tariff_name[0]["name"])
                                        full_tariff_flag = 1

                        except:
                            logs.append("No Full Tariff Found. Using Default Tariff")
                            print("No Full Tariff Found. Using Default Tariff")
                            full_tariff = frappe.get_doc("Full Tariff", definition.default_selling_rate)

                    # **Calculate Rate if Full Tariff is Found**
                    if full_tariff:
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        flg = 0
                        last_row = {}

                        for row in full_tariff.package_rate:
                            if my_weight <= row.weight:
                                final_rate = row.rate
                                flg = 1
                                break
                            else:
                                last_row = row

                        if flg == 0:
                            final_rate = (last_row.rate / last_row.weight) * my_weight
                            final_discount_percentage = 0.00
                        tarif = final_rate / (1- (final_discount_percentage/100))
                        

                        print(f"Final Rate from Full Tariff: {tarif}")

                    else:
                        print("Full Tariff Not Found, Switching to Selling Rate Logic")




                if selling_group and full_tariff_flag == 0:
                    
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
                        try:
                            countries = frappe.db.get_all("Country Names", filters={"countries":origin_country} , fields = ['parent'])
                            
                            if countries:
                                zone_with_out_country = countries[0].parent
                                print("Zone with Country :",zone_with_out_country)
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
                                        selling_rate = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                        
                                    else :
                                        logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                        print("No Selling Rate Found Thats Why using Default Selling Rate")
                                        if definition.default_selling_rate:
                                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)

                            else:
                                logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                print("No Selling Rate Found Thats Why using Default Selling Rate")
                                if definition.default_selling_rate:
                                    selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                        except:
                            logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                            print("No Selling Rate Found Thats Why using Default Selling Rate")
                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
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
            
        codes_incl_fuel = []
        amounts_incl_fuel = []
        surcharge_codes_incl_fuel = []

        codes_other_charges = []
        amounts_other_charges = []
        surcharge_codes_other_charges = []

        if doctype_name:

            r201 = frappe.get_list(
                "R201000",
                filters={'shipment_number': shipment_number},
            )
            
            if r201:
                docn = frappe.get_doc("R201000", r201[0].name)
                
                # Fetch customer applicable surcharges using sales_invoice.customer
                customer_surcharges = frappe.get_all(
                    "Customer Surcharges Table",
                    filters={'parent': sales_invoice.customer}, 
                    fields=['surcharge', 'amount']
                )
                
                exempt_codes = frappe.get_all(
                    "Exempt Codes",
                    filters={'parent': sales_invoice.customer}, 
                    fields=['code']
                )
                # Create a dictionary of customer surcharges (code: amount)
                surcharge_dict = {item['surcharge']: item['amount'] for item in customer_surcharges}
                exempt_code_list = [item['code'] for item in exempt_codes]
                for row in definition.surcharges:
                    code_name = row.sur_cod_1
                    amount_name = row.sur_amt_1
                    code = getattr(docn, code_name, None)
                    amount = getattr(docn, amount_name, None)
                    surcharge_amount = surcharge_dict.get(code)

                    
                    if surcharge_amount is not None:
                        if surcharge_amount > 0:
                            amount = surcharge_amount
                    else:
                        if amount is not None:
                            try:
                                amount = float(amount)
                            except (ValueError, TypeError):
                                amount = 0

                    if code in exempt_code_list:
                        print(code in included_codes and code not in excluded_codes)
                        continue

                    if code in included_codes and code not in excluded_codes:
                        codes_incl_fuel.append(code)
                        amounts_incl_fuel.append(amount)
                        surcharge_codes_incl_fuel.append(code_name)
                    elif code not in included_codes and code not in excluded_codes:
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
        FSCpercentage = frappe.db.get_single_value('Additional Charges Page','feul_surcharge_percentage_on_freight_amount')
        additional_page = frappe.get_doc("Additional Charges Page")
        for row in additional_page.fuel_surcharge_percentages_on_freight_amount:
            if row.expiry_date < shipped_date:  
                latest_valid_percentage = row.fuel_surcharge_percentage_on_freight_amount
            
            if row.from_date <= shipped_date <= row.expiry_date:
                FSCpercentage = row.fuel_surcharge_percentage_on_freight_amount
                break
        print(FSCpercentage ,latest_valid_percentage )
        if FSCpercentage == 0 and latest_valid_percentage != 0:
            FSCpercentage = latest_valid_percentage
        
        if FSCpercentage and final_rate:
                print(FSCpercentage)
                print(final_rate)
                FSCcharges = (total_charges_incl_fuel + final_rate) * (FSCpercentage / 100 )
        shipmentbillingcheck = 0
        shipmentbillingamount = 0
        shipmentbillingchargesfromcustomer = 0
        sbc_flag = 0
        if sales_invoice.customer:
            customer_doc = frappe.get_doc("Customer",sales_invoice.customer)
            shipmentbillingcheck = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipping_bill_charges_applicable')
            if shipmentbillingcheck and shipment_type in sbc_included and shipment_type not in sbc_excluded:
                if shipmentbillingcheck and customer_doc.custom_shipping_billing_charges:
                        for row in customer_doc.custom_shipping_billing_charges:
                            if float(row.from_weight) <= float(sales_invoice.custom_shipment_weight) <= float(row.to_weight):
                                shipmentbillingamount = row.amount
                                sbc_flag = 1
                                break
                if imp_exp == "Export" and sbc_flag == 0:
                    shipmentbillingamount = frappe.db.get_single_value('Additional Charges Page', 'export_amount_per_shipment')
                    
                elif imp_exp == "Import" and sbc_flag == 0:
                    shipmentbillingamount = frappe.db.get_single_value('Additional Charges Page', 'import_amount_per_shipment')







        declared_value = sales_invoice.custom_insurance_amount
        if declared_value is None:
            declared_value = 0  
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
            sales_invoice.custom_freight_invoices = 1
            if declared_value > 0:            
                percent = frappe.db.get_single_value('Additional Charges Page', 'percentage_on_declare_value')
                minimum_amount = frappe.db.get_single_value('Additional Charges Page', 'minimum_amount_for_declare_value')
                result = declared_value * (percent / 100)
                max_insured = max(result , minimum_amount)
                
                if max_insured > 0 and shipment_type == setting.insurance_shipment_type:
                    print("Max Insured")
                    rows = {'item_code': setting.insurance_charges, 'qty': '1', 'rate': max_insured}
                    sales_invoice.append('items', rows)
            sales_invoice.discount_amount = tarif - final_rate
            sales_invoice.custom_amount_after_discount = tarif - sales_invoice.discount_amount
            
            if sales_invoice.custom_selling_percentage:
                final_discount_percentage = sales_invoice.custom_selling_percentage
            if not sales_invoice.custom_selling_percentage:
                sales_invoice.custom_selling_percentage = final_discount_percentage



            print(total_charges_other_charges,FSCcharges,tarif , shipmentbillingamount , total_charges_incl_fuel)
            if total_charges_other_charges:
                rows = {'item_code': setting.other_charges, 'qty': 1 , 'rate' :total_charges_other_charges} 
                
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

            if total_charges_incl_fuel:
                rows = {'item_code' : setting.include_fuel_charges , 'qty' : '1' , 'rate' : total_charges_incl_fuel}
                
                sales_invoice.append('items' , rows)
            additional_surcharges_page = frappe.get_doc("Additional Charges Page")
            peak_amount = 0
            if additional_surcharges_page.peak_charges_duration_and_amount:    
                for row in additional_surcharges_page.peak_charges_duration_and_amount:
                    if row.from_date <= shipped_date <= row.to_date:
                        if sales_invoice.custom_shipment_weight <= 0.5:
                            peak_amount = row.amount
                            break
                        elif sales_invoice.custom_shipment_weight > 0.5:
                            peak_amount = sales_invoice.custom_shipment_weight * (row.amount)
            if peak_amount:
                rows = {'item_code' : setting.peak_charges , 'qty' : '1' , 'rate' : peak_amount}
                sales_invoice.append('items' , rows)



        export_compensation_amount = 0

        
        if sales_invoice.customer == customer.custom_default_customer:
            exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
            if not exempt_customer:
                sales_invoice.taxes_and_charges= None
                sales_invoice.taxes = []
            sales_invoice.custom_compensation_invoices = 1
            sig = 0
            for comp in definition.compensation_table:
                if sales_invoice.custom_billing_term == comp.shipment_billing_term and shipment_type == comp.shipping_billing_type and imp_exp == comp.case:
                    export_compensation_amount = comp.document_amount
                    
                    rows = {'item_code': setting.compensation_charges , 'qty': '1', 'rate': export_compensation_amount}
                    sales_invoice.append('items', rows)
                    sig = 1
                    break
        
        if not sales_invoice.items:
            print(sales_invoice.customer)
            logs.append(f"No Items shipment number {shipment_number}, icris number {icris_number}")
            log_text = "\n".join(logs)
            log_doc.set("shipment_number" , shipment_number)
            log_doc.set("logs", log_text)
            log_doc.set("icris_number" , icris_number)
            log_doc.save()
            print("No Items")
            return
        
        log_text = "\n".join(logs)
        discounted_amount = discounted_amount -1
        sales_invoice.set_missing_values()

        #################### Sufyan Edit in Fariz Code As Per KashiBhai Instruction #######################
        if frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst') :
            self.taxes_and_charges = None
            self.taxes = []
        #################### Sufyan Edit in Fariz Code As Per KashiBhai Instruction #######################

        sales_invoice.calculate_taxes_and_totals()
        # sales_invoice.validate()
        print(sales_invoice.customer_name)
        # sales_invoice.save()
        print(sales_invoice.name)
        if logs:
            log_doc.set("shipment_number" , shipment_number)
            log_doc.set("logs", log_text)
            log_doc.set("icris_number" , icris_number)
            if not log_doc.sales_invoice:
                log_doc.set("sales_invoice",sales_invoice.name)
            log_doc.save()
        
        frappe.db.commit()
            
# def after_save_sales_invoice(self,method):
#     print("After save is working")
#     sales_invoice = self
#     log_list = frappe.get_list("Sales Invoice Logs",filters ={"shipment_number":sales_invoice.custom_shipment_number})
#     print(log_list)
#     if log_list:
#         log_doc = frappe.get_doc("Sales Invoice Logs",log_list[0].name)
#         log_doc.set("sales_invoice",sales_invoice.name)
#         log_doc.save()