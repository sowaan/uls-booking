from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, cint
import re
import logging


def get_exchange_rate(from_currency, to_currency, date):
    filters = {"from_currency": from_currency, "to_currency": to_currency, "date": date}
    rate = frappe.get_list("Currency Exchange", filters=filters, fields=["exchange_rate"], order_by="date desc", limit_page_length=1)

    if not rate:
        filters["date"] = ["<", date]
        rate = frappe.get_list("Currency Exchange", filters=filters, fields=["exchange_rate"], order_by="date desc", limit_page_length=1)

    return rate[0].exchange_rate if rate else 0

def generate_invoice(self, method):
    
    # return
    # print("Generating Invoice")
    sales_invoice = self
    if sales_invoice.custom_edit_items:
        edit_items = sales_invoice.get("items")
    # if not self.customer == "UPS Compensation":
    #     return
    # frappe.throw("Generating Invoice")
    if sales_invoice.custom_duty_and_taxes_invoice == 1:
        if self.taxes_and_charges :
            self.taxes_and_charges = None
            self.taxes = []
        return

    # third_party_ind = frappe.db.get_value("R200000", {'shipment_number': sales_invoice.custom_shipment_number}, 'third_party_indicator_code') if sales_invoice.custom_shipment_number else None
    # print(sales_invoice.custom_shipment_number, "custom_shipment_number \n\n\n")
    if not sales_invoice.custom_compensation_invoices and not sales_invoice.custom_freight_invoices:
        if sales_invoice.custom_shipment_number:
            third_party_ind_list = frappe.db.sql("""
                SELECT IFNULL(third_party_indicator_code, 0) 
                FROM `tabR200000` 
                WHERE shipment_number = %s
            """, sales_invoice.custom_shipment_number, as_dict=False)
            if third_party_ind_list :
                third_party_ind = third_party_ind_list[0][0]
                sales_invoice.set('custom_third_party_indicator_code', third_party_ind)
            else:
                third_party_ind = None
        else:
            third_party_ind = None

        if third_party_ind and third_party_ind != "0":
            # print("compensation")
            sales_invoice.set('custom_compensation_invoices', True)
            sales_invoice.set('custom_freight_invoices', False)
        elif third_party_ind and third_party_ind == '0':
            # print("freight")
            sales_invoice.set('custom_compensation_invoices', False)
            sales_invoice.set('custom_freight_invoices', True)
         



    shipment_number = sales_invoice.custom_shipment_number
    log_list = frappe.get_list("Sales Invoice Logs", filters={"shipment_number": shipment_number})
    log_doc = frappe.get_doc("Sales Invoice Logs", log_list[0].name) if log_list else frappe.new_doc("Sales Invoice Logs")
    
    logs = []
    discounted_amount = 0
    selling_rate_country = 0
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

    export_billing_term = [term.billing_term for term in definition.export_and_import_conditions if term.export_check == 1]
    import_billing_term = [term.billing_term for term in definition.export_and_import_conditions if  term.export_check == 0]
    
    for code in setting.surcharges_code_excl_and_incl:
        excluded_codes.append(code.excluded_codes)
        included_codes.append(code.included_codes)
    
    discounted_amount = discounted_amount + 1
    final_rate = 0
    tarif = 0
    final_discount_percentage = 0
    origin_country = None
    
    company = definition.default_company
    customer = frappe.get_doc("Company",company)

    end_date = sales_invoice.posting_date
    total_charges_incl_fuel = 0
    total_charges_other_charges = 0
    FSCcharges = 0
    FSCpercentage = 0
    latest_valid_percentage = 0
    shipment_type = 0
    date2 = getdate(end_date)
    sales_invoice.posting_date = date2
    sales_invoice.set_posting_time = 1
    exempt_customer = 0



    icris_number = None
    selling_group = None
    selling_rate = None
    shipped_date = getdate(sales_invoice.custom_date_shipped)
    #print(shipped_date, "shipped Date \n\n")
    sales_invoice.conversion_rate = get_exchange_rate("USD", "PKR", shipped_date)
    if sales_invoice.custom_shipper_country:
        is_export = sales_invoice.custom_shipper_country.upper() == definition.origin_country.upper()
    else:
        is_export = sales_invoice.custom_shipper_country == definition.origin_country.upper()
    imp_exp = "Export" if is_export else "Import"
    if is_export:
        icris_number = sales_invoice.custom_shipper_number or definition.unassigned_icris_number
    else:
        icris_number = sales_invoice.custom_consignee_number or definition.unassigned_icris_number
    
    # Assign shipment type
    shipment_type = sales_invoice.custom_package_type or sales_invoice.custom_shipment_type
        
    try:
        icris_account = frappe.get_doc("ICRIS Account", icris_number)
    
    except frappe.DoesNotExistError:
        logs.append(f"No icris Account Found {icris_number}")
        #print("No icris Account Found")
        if definition.unassigned_icris_number:
            icris_account = frappe.get_doc("ICRIS Account", definition.unassigned_icris_number)
    #print(shipment_type, "shipment_type \n\n\n")
    # print('hello')
    # print("sales_invoice.custom_freight_invoices", sales_invoice.custom_freight_invoices)
    # print("sales_invoice.custom_compensation_invoices", sales_invoice.custom_compensation_invoices)
    if sales_invoice.custom_freight_invoices:
        # if sales_invoice.custom_billing_term in export_billing_term and is_export:
        if is_export:
            check1 = frappe.get_list("ICRIS Account", filters = {"name":icris_number})
            if not check1:
                logs.append(f"No ICRIS Account Found {icris_number}")
                #print("No ICRIS Account Found")
                icris_number = definition.unassigned_icris_number
            #print('\n\n\n\n\n\n\n\n icris_number \n\n\n\n\n', icris_number, '\n\n\n')
            if icris_number:
                icris_doc = frappe.get_list("ICRIS Account", filters={"name": icris_number})
                icris = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                if icris.shipper_name:
                    # sales_invoice.customer = icris.shipper_name
                    sales_invoice.set("customer", icris.shipper_name)
                    #print('\n\n\n\n\n\n\nn\n icris.shipper_name \n\n\n\nn\n')

                    r300000_list = frappe.get_list('R300000', filters={'shipment_number' : shipment_number})
                    
                    if r300000_list:
                        r300000_doc = frappe.get_doc('R300000', r300000_list[0].name)
                        if r300000_doc.alternate_tracking_number_1 and r300000_doc.alternate_tracking_number_1 != '':
                            cust_list = frappe.get_list('Customer',
                                                        filters={
                                            'disabled' : ['!=',1] ,
                                            'custom_import_account_no' : r300000_doc.alternate_tracking_number_1
                                        }
                                    )
                            if cust_list:
                                # sales_invoice.customer = cust_list[0].name
                                sales_invoice.set("customer", cust_list[0].name)
                                #print('\n\n\n\n\n\n\nn\n cust_list[0].name \n\n\n\nn\n')
                                sales_invoice.custom_account_no = r300000_doc.alternate_tracking_number_1

                    # customer_name = frappe.db.get_value("Customer", sales_invoice.customer, ['customer_name', 'custom_import_account_no', 'custom_billing_type'], as_dict=True)
                    # sales_invoice.customer_name = customer_name.customer_name
                    # sales_invoice.custom_billing_type = customer_name.custom_billing_type
                    # sales_invoice.custom_account_no = customer_name.custom_import_account_no
                else:
                    logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}")
                    #print("No Customer Found")
                exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
                tax_rule = None
                tax_rule_name = None
                if exempt_customer == 0:
                    if frappe.db.exists("Territory", {"name": sales_invoice.custom_shipper_city}):
                        tt = frappe.get_doc("Territory", sales_invoice.custom_shipper_city)
                    else:
                        tt = None

                    #print(tt.name, "Territory Name \n\n\n")
                    if tt:
                        pt = tt.parent_territory
                        #print(pt, "parent_territory \n\n")
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

                                        # logs.append(f"No Territory Found '{sales_invoice.custom_shipper_city}'.So Using default Tax")
                                        #print("No Territory Found so Using default Tax")
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

                            # logs.append(f"No Territory Found '{sales_invoice.custom_shipper_city}'.So Using default Tax")
                            #print("No Territory Found so Using default Tax")

                
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
                        #print("No selling group Found thats why using Default Selling group")
                        selling_group = definition.default_selling_group 
                full_tariff_flag = 0
                
                #print(selling_group , " = ", definition.default_selling_group, "Group \n\n\n")

                if selling_group == definition.default_selling_group:
                    # Look for Full Tariff
                    zones = frappe.get_list("Zone",
                                            filters = {"country" : origin_country , "is_single_country":1})
                    flag = 0
                    
                    if zones:
                        sales_invoice.custom_zone = zones[0].name
                        #print("Zone with Country:", zones[0].name)

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
                            #print("No Full Tariff Found. Using Default Tariff")

                    # **Calculate Rate if Full Tariff is Found**
                    if full_tariff:
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        flg = 0
                        last_row = {}

                        for row in full_tariff.package_rate:
                            if my_weight <= row.weight:
                                final_rate = row.rate
                                # print('row_02', final_rate, 'row_02')
                                flg = 1
                                break
                            else:
                                last_row = row

                        if flg == 0:
                            final_rate = (last_row.rate / last_row.weight) * my_weight
                            # print('last_row_02', final_rate, 'last_row_02')
                            final_discount_percentage = 0.00
                        tarif = final_rate / (1- (final_discount_percentage/100))
                        #print(final_rate)
                        
                        

                        #print(f"Final Rate from Full Tariff: {tarif}")

                    else:
                        pass
                        # **If Full Tariff is NOT found, switch to Selling Rate Logic**
                        #print("Full Tariff Not Found, Switching to Selling Rate Logic")



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
                            #print(selling_rate)
                            
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
                                        #print(selling_rate)
                                        
                                    else :
                                        logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                        #print("No Selling Rate Found Thats why using Default Selling Rate")
                                        if definition.default_selling_rate:
                                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                                            #print(selling_rate)
                            else:
                                logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                #print("No Selling Rate Found Thats Why using Default Selling Rate")
                                if definition.default_selling_rate:
                                    selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)    
                                    #print(selling_rate)          
                        except:
                            logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                            #print("No Selling Rate Found Thats why using Default Selling Rate")
                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                            #print("Selling Rate",selling_rate)
                            
                    
                    my_weight = float(sales_invoice.custom_shipment_weight)
                    if selling_rate :
                        flg = 0
                        last_row = {}
                        for row in selling_rate.package_rate :

                            if my_weight <= row.weight :
                                final_rate = row.rate
                                # print('row_01', final_rate, 'row_01')
                                final_discount_percentage = row.discount_percentage
                                flg = 1
                                break
                            else :
                                last_row = row
                        if flg == 0 :
                            final_rate = ( last_row.rate / last_row.weight ) * my_weight
                            # print('last_row_01', final_rate, 'last_row_01')
                            final_discount_percentage = last_row.discount_percentage
                        tarif = final_rate / (1- (final_discount_percentage/100))
                        #print(final_rate)
            # print('hello2')
        # elif sales_invoice.custom_billing_term in import_billing_term and sales_invoice.custom_shipper_country != definition.origin_country.upper():
        else:
            # print('hello3')
            # print(icris_number, "icris number \n\n\n")
            check = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
            if not check:
                logs.append(f"No ICRIS Account Found {icris_number}")
                #print("No ICRIS Account Found Thats Why using Default Icris")
                icris_number = definition.unassigned_icris_number
            if icris_number:
                icris_doc = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
                icris1 = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                
                if icris1.shipper_name:
                    # sales_invoice.customer = icris1.shipper_name
                    sales_invoice.set("customer", icris1.shipper_name)
                    # print('\n\n\n\n\n\n\nn\n', icris1.shipper_name,' \n\n\n\nn\n')
                    
                    r300000_list1 = frappe.get_list('R300000',
                                        filters={
                                            'shipment_number' : shipment_number
                                        }
                                    )
                    if r300000_list1 :
                        r300000_doc = frappe.get_doc('R300000', r300000_list1[0].name)
                        if r300000_doc.alternate_tracking_number_1 and r300000_doc.alternate_tracking_number_1 != '':
                            cust_list = frappe.get_list('Customer',
                                        filters={
                                            'disabled' : ['!=',1] ,
                                            'custom_import_account_no' : r300000_doc.alternate_tracking_number_1
                                        }
                                    )
                            if cust_list :
                                # sales_invoice.customer = cust_list[0].name
                                sales_invoice.set("customer", cust_list[0].name)
                                # #print('\n\n\n\n\n\n\nn\n cust_list[0].name \n\n\n\nn\n')
                                sales_invoice.custom_account_no = r300000_doc.alternate_tracking_number_1
                                
                    # customer_name = frappe.db.get_value("Customer", sales_invoice.customer, ['customer_name', 'custom_import_account_no', 'custom_billing_type'], as_dict=True)
                    # sales_invoice.customer_name = customer_name.customer_name
                    # sales_invoice.custom_billing_type = customer_name.custom_billing_type
                    # sales_invoice.custom_account_no = customer_name.custom_import_account_no
                    
                else:
                    logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}") 
                    #print("No Customer Found")
                exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
                tax_rule = None
                tax_rule_name = None
                tax_flag = 0
                if exempt_customer == 0:
                    if frappe.db.exists("Territory", {"name": sales_invoice.custom_shipper_city}):
                        mm = frappe.get_doc("Territory", sales_invoice.custom_consignee_city)
                    else:
                        mm = None
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
                                    # logs.append(f"No Territory Found '{sales_invoice.custom_consignee_city}'.So Using default Tax")
                                    #print("No Territory Found Thats Why using Default Sales Tax and Template")
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
                        # logs.append(f"No Territory Found '{sales_invoice.custom_consignee_city}'.So Using default Tax")
                        #print("No Territory Found Thats Why using Default Sales Tax and Template")
                if sales_invoice.custom_shipper_country:
                    origin_country = sales_invoice.custom_shipper_country
                    origin_country = origin_country.capitalize()
                zone_with_out_country = None
                selling_rate_name = None
                service_type = frappe.get_list("Service Type",
                                    filters = {"imp__exp":imp_exp , "service": sales_invoice.custom_service_type})
                # print('service_type', service_type, 'service_type')
                # print('imp_exp', imp_exp, 'imp_exp')
                # print('custom_service_type', sales_invoice.custom_service_type, 'custom_service_type')
                
                if service_type:
                    for icris in icris_account.rate_group:
                        if  icris.service_type == service_type[0].get("name")  and icris.from_date <= shipped_date <= icris.to_date:
                            selling_group = icris.rate_group
                            break
                if not selling_group:
                    logs.append(f"No selling group Found thats why using Default Selling group")
                    #print("No Selling Group Found Thats why using Default Selling Group")
                    selling_group = definition.default_selling_group
                full_tariff_flag = 0
                
                #print(selling_group , " = ", definition.default_selling_group)

                if selling_group == definition.default_selling_group:
                    # Look for Full Tariff
                    zones = frappe.get_list("Zone", filters={"country": origin_country, "is_single_country": 1})
                    flag = 0
                    if zones:
                        sales_invoice.custom_zone = zones[0].name
                        # print("Zone with Country:", zones[0].name)

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
                            #print("No Full Tariff Found. Using Default Tariff")
                            full_tariff = frappe.get_doc("Full Tariff", definition.default_selling_rate)

                    # **Calculate Rate if Full Tariff is Found**
                    if full_tariff:
                        my_weight = float(sales_invoice.custom_shipment_weight)
                        flg = 0
                        last_row = {}

                        for row in full_tariff.package_rate:
                            if my_weight <= row.weight:
                                final_rate = row.rate
                                # print('row_0', final_rate, 'row_0')
                                flg = 1
                                break
                            else:
                                last_row = row

                        if flg == 0:
                            final_rate = (last_row.rate / last_row.weight) * my_weight
                            # print('last_row_0', final_rate, 'last_row_0')
                            final_discount_percentage = 0.00
                        tarif = final_rate / (1- (final_discount_percentage/100))
                        

                        #print(f"Final Rate from Full Tariff: {tarif}")

                    else:
                        pass
                        #print("Full Tariff Not Found, Switching to Selling Rate Logic")



                if selling_group and full_tariff_flag == 0:
                    zones = frappe.get_list("Zone",
                                            filters = {"country" : origin_country , "is_single_country":1})
                    
                    flag = 0
                    if zones:
                        sales_invoice.custom_zone = zones[0].name
                        #print("Zone with Country :",zones[0].name)
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
                                #print("Zone with Country :",zone_with_out_country)
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
                                        #print("No Selling Rate Found Thats Why using Default Selling Rate")
                                        if definition.default_selling_rate:
                                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)

                            else:
                                logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                #print("No Selling Rate Found Thats Why using Default Selling Rate")
                                if definition.default_selling_rate:
                                    selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                        except:
                            logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                            #print("No Selling Rate Found Thats Why using Default Selling Rate")
                            selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                    my_weight = float(sales_invoice.custom_shipment_weight)
                    if selling_rate :
                        flg = 0
                        last_row = {}
                        for row in selling_rate.package_rate:
                            if my_weight <= row.weight :
                                final_rate = row.rate
                                # print('row', final_rate, 'row')
                                final_discount_percentage = row.discount_percentage
                                flg = 1
                                break
                            else :
                                last_row = row
                        if flg == 0 :
                            final_rate = ( last_row.rate / last_row.weight ) * my_weight
                            # print('last_row', final_rate, 'last_row')
                            final_discount_percentage = last_row.discount_percentage
                        tarif = final_rate / (1- (final_discount_percentage/100))
        # print('hello4')
        codes_incl_fuel = []
        amounts_incl_fuel = []
        surcharge_codes_incl_fuel = []

        codes_other_charges = []
        amounts_other_charges = []
        surcharge_codes_other_charges = []

        r201 = frappe.get_list("R201000", filters={'shipment_number': shipment_number},)
        
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
                    #print(code in included_codes and code not in excluded_codes, "841 \n\n\n\n")
                    continue
                #print(code in included_codes and code not in excluded_codes, "ture or false value 843 \n\n")
                #print(code not in included_codes and code not in excluded_codes, "ture or false value 844 \n\n")
                if code in included_codes and code not in excluded_codes:
                    codes_incl_fuel.append(code)
                    amounts_incl_fuel.append(amount)
                    surcharge_codes_incl_fuel.append(code_name)
                elif code not in included_codes and code not in excluded_codes:
                    codes_other_charges.append(code)
                    amounts_other_charges.append(amount)
                    surcharge_codes_other_charges.append(code_name)

        # print('hello5')
        sales_invoice.custom_surcharge_excl_fuel = []
        total_charges_incl_fuel = sum(amounts_incl_fuel)
        total_charges_other_charges = sum(amounts_other_charges)
        #print(surcharge_codes_other_charges, codes_other_charges, amounts_other_charges, "858 amount \n\n\n")
        for surcharge_code, code, amount in zip(surcharge_codes_other_charges, codes_other_charges, amounts_other_charges):
            #print(surcharge_code, code, amount, "860 sales invoice \n\n\n\n")
            if code: 
                sales_invoice.append("custom_surcharge_excl_fuel", {
                    "surcharge": surcharge_code, 
                    "code": code,                
                    "amount": amount             
                })
        sales_invoice.custom_surcharge_incl_fuel = []

        #print(surcharge_codes_incl_fuel, codes_incl_fuel, amounts_incl_fuel, "869 amount \n\n\n")
        for surcharge_code, code, amount in zip(surcharge_codes_incl_fuel, codes_incl_fuel, amounts_incl_fuel):
            #print(surcharge_code, code, amount, "871 sales invoice \n\n\n\n")
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
        #print(FSCpercentage ,latest_valid_percentage )
        if FSCpercentage == 0 and latest_valid_percentage != 0:
            FSCpercentage = latest_valid_percentage
        
        if FSCpercentage and final_rate:
                #print(FSCpercentage)
                #print(final_rate)
                FSCcharges = (total_charges_incl_fuel + final_rate) * (FSCpercentage / 100 )
        shipmentbillingcheck = 0
        shipmentbillingamount = 0
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
                pass
                #print("")
        else:
            pass
            #print("")
        max_insured = 0
        if sales_invoice.customer != customer.custom_default_customer:
            sales_invoice.custom_freight_invoices = 1
            if declared_value > 0:
                percent = frappe.db.get_single_value('Additional Charges Page', 'percentage_on_declare_value')
                minimum_amount = frappe.db.get_single_value('Additional Charges Page', 'minimum_amount_for_declare_value')
                result = declared_value * (percent / 100)
                max_insured = max(result , minimum_amount)
                
                # if max_insured > 0 and shipment_type == setting.insurance_shipment_type:
                if max_insured > 0 and sales_invoice.custom_shipment_type == setting.insurance_shipment_type:
                    #print("Max Insured")
                    rows = {'item_code': setting.insurance_charges, 'qty': '1', 'rate': max_insured}
                    sales_invoice.append('items', rows)
            sales_invoice.custom_freight_charges = tarif
            # frappe.throw(str(final_rate))
            amt = tarif - final_rate
            sales_invoice.discount_amount = round(amt, 2) or 0
            sales_invoice.base_discount_amount = (sales_invoice.discount_amount or 0)  * (sales_invoice.conversion_rate or 0)
            # frappe.msgprint(str(sales_invoice.conversion_rate))
            # frappe.msgprint(str(sales_invoice.discount_amount))
            # frappe.msgprint(str(sales_invoice.base_discount_amount))

            sales_invoice.custom_amount_after_discount = tarif - (sales_invoice.discount_amount or 0)
            
            # if sales_invoice.custom_edit_selling_percentage == 1:
            #     final_discount_percentage = sales_invoice.custom_selling_percentage or 0
            #     sales_invoice.discount_amount = (sales_invoice.custom_freight_charges * final_discount_percentage / 100)
            #     sales_invoice.custom_amount_after_discount = sales_invoice.custom_freight_charges - sales_invoice.discount_amount
            # else:
            #     sales_invoice.custom_selling_percentage = final_discount_percentage
            #     sales_invoice.custom_inserted = 1


            #print(total_charges_other_charges,FSCcharges,tarif , shipmentbillingamount , total_charges_incl_fuel)
            if total_charges_other_charges:
                sales_invoice.append('items', {'item_code': setting.other_charges, 'qty': 1 , 'rate' :total_charges_other_charges})
            if FSCcharges:
                sales_invoice.append('items', {'item_code': setting.fuel_charges, 'qty': '1', 'rate': FSCcharges})
            if tarif:
                sales_invoice.append('items' , {'item_code' : setting.freight_charges , 'qty' : '1' , 'rate' : tarif})
            if shipmentbillingamount:
                sales_invoice.append('items' , {'item_code' : setting.shipment_billing_charges , 'qty' : '1' , 'rate' : shipmentbillingamount})
            if total_charges_incl_fuel:
                sales_invoice.append('items' , {'item_code' : setting.include_fuel_charges , 'qty' : '1' , 'rate' : total_charges_incl_fuel})
            
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
            
            exempt_peak_surcharge = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_peak_surcharge')
            if peak_amount and exempt_peak_surcharge != 1 :
                rows = {'item_code' : setting.peak_charges , 'qty' : '1' , 'rate' : peak_amount}
                sales_invoice.append('items' , rows)

        if sales_invoice.custom_edit_items:
            sales_invoice.items = edit_items
            freight_in_items = next(
                    (item_row.amount for item_row in sales_invoice.items if item_row.item_code == setting.freight_charges),0
                )
            # print("freight_in_items", freight_in_items)
            sales_invoice.custom_freight_charges = freight_in_items


    elif sales_invoice.custom_compensation_invoices:
        

        export_compensation_amount = 0
        
        if sales_invoice.customer == customer.custom_default_customer:
            exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
            if not exempt_customer:
                sales_invoice.taxes_and_charges = None
                sales_invoice.taxes = []
            sales_invoice.custom_compensation_invoices = 1
            for comp in definition.compensation_table:
                
                # if sales_invoice.custom_billing_term == comp.shipment_billing_term and shipment_type == comp.shipping_billing_type and imp_exp == comp.case:
                #     export_compensation_amount = comp.document_amount
                #     sales_invoice.append('items', {'item_code': setting.compensation_charges , 'qty': '1', 'rate': export_compensation_amount})
                #     break
                if sales_invoice.custom_billing_term == comp.shipment_billing_term and self.custom_shipment_type == comp.shipping_billing_type and imp_exp == comp.case:
                    print('condition true')
                    export_compensation_amount = comp.document_amount
                    sales_invoice.append('items', {'item_code': setting.compensation_charges , 'qty': '1', 'rate': export_compensation_amount})
                    break

    print(sales_invoice.items)
    print(sales_invoice.customer)
    # print(export_compensation_amount, "export_compensation_amount")
    # print("setting.compensation_charges", setting.compensation_charges)
    if sales_invoice.custom_edit_selling_percentage == 1:
        final_discount_percentage = sales_invoice.custom_selling_percentage or 0
        sales_invoice.discount_amount = (sales_invoice.custom_freight_charges * final_discount_percentage / 100)
        sales_invoice.custom_amount_after_discount = sales_invoice.custom_freight_charges - sales_invoice.discount_amount
    else:
        sales_invoice.custom_selling_percentage = final_discount_percentage
        sales_invoice.custom_inserted = 1

        

    if not sales_invoice.items:
        # print('\n\n\n\n\n\n\nn\n No Items \n\n\n\nn\n')
        logs.append(f"No Items shipment number {shipment_number}, icris number {icris_number}")
        log_text = "\n".join(logs)
        if frappe.db.exists("Shipment Number", shipment_number):
            log_doc.set("shipment_number" , shipment_number)
        log_doc.set("logs", log_text)
        if frappe.db.exists("ICRIS Account", icris_number):
            log_doc.set("icris_number" , icris_number)
        log_doc.save()
        return
    if sales_invoice.custom_edit_selling_percentage:
        for row in sales_invoice.items:
            if row.item_code == setting.fuel_charges:
                per = get_fuel_percentage_for_date(sales_invoice.custom_date_shipped)
                row.rate = ((sales_invoice.custom_amount_after_discount + sales_invoice.custom_total_surcharges_incl_fuel) * per) / 100


    customer = frappe.db.get_value("Customer", sales_invoice.customer, ['customer_name', 'custom_import_account_no', 'custom_billing_type', 'payment_terms'], as_dict=True)
    sales_invoice.customer_name = customer.customer_name

    

    # sales_invoice.custom_billing_type = customer.custom_billing_type
    # sales_invoice.custom_account_no = customer.custom_import_account_no
    # sales_invoice.set('payment_terms_template', customer.payment_terms)
    # if sales_invoice.payment_schedule:
    #     sales_invoice.payment_schedule[0].set("payment_term", customer.payment_terms)


    discounted_amount = discounted_amount -1
    get_sales_tax(self, logs)
    log_text = "\n".join(logs)
    sales_invoice.set_missing_values()
    #################### Sufyan Edit in Fariz Code As Per KashiBhai Instruction #######################
    if frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst') :
        self.taxes_and_charges = None
        self.taxes = []
    #################### Sufyan Edit in Fariz Code As Per KashiBhai Instruction #######################

    sales_invoice.calculate_taxes_and_totals()
    # sales_invoice.validate()
    #print(sales_invoice.customer_name)
    # sales_invoice.save()
    #print(sales_invoice.name)
    if logs:
        if frappe.db.exists("Shipment Number", shipment_number):
            log_doc.set("shipment_number" , shipment_number)
        if frappe.db.exists("ICRIS Account", icris_number):
            log_doc.set("icris_number" , icris_number)
        log_doc.set("logs", log_text)
        log_doc.save()
        # if not log_doc.sales_invoice:
        #     log_doc.set("sales_invoice",sales_invoice.name)
    # else:
        
        # if not log_doc.sales_invoice:
        #     log_doc.set("sales_invoice", sales_invoice.name)

    
    
    frappe.db.commit()
    



def get_sales_tax(self, logs) :


    if self.custom_freight_invoices == 1 :

        self.set('taxes_and_charges', None)
        self.taxes = []
        ret = check_for_shipper_city(self)
        if not ret :
            ret1 = check_for_consignee_city(self)
            if not ret1 :
                set_default_tax(self)
                logs.append("No Territory Found.So Using default Tax.")








def check_for_shipper_city(self) :
    if self.custom_shipper_city :
        sales_tax_list = frappe.get_all('Sales Taxes and Charges Template', 
                            filters = {
                                'custom_province' : self.custom_shipper_city
                            }
                        )
        if sales_tax_list :
            sales_tax_doc = frappe.get_doc('Sales Taxes and Charges Template', sales_tax_list[0].name)
            self.set('taxes_and_charges', sales_tax_doc.name)
            for sale in sales_tax_doc.taxes:
                rows = {
                    'charge_type': sale.charge_type,
                    'description': sale.description,
                    'account_head': sale.account_head,
                    'cost_center': sale.cost_center,
                    'rate': sale.rate,
                    'account_currency': sale.account_currency
                }
                self.append('taxes', rows)
            return True
        
        else :
            if frappe.db.exists('Territory', self.custom_shipper_city) :
                parent_territory = frappe.db.get_value('Territory', self.custom_shipper_city, 'parent_territory')
                sales_tax_list = frappe.get_all('Sales Taxes and Charges Template', 
                            filters = {
                                'custom_province' : parent_territory
                            }
                        )
                if sales_tax_list :
                    sales_tax_doc = frappe.get_doc('Sales Taxes and Charges Template', sales_tax_list[0].name)
                    self.set('taxes_and_charges', sales_tax_doc.name)
                    for sale in sales_tax_doc.taxes:
                        rows = {
                            'charge_type': sale.charge_type,
                            'description': sale.description,
                            'account_head': sale.account_head,
                            'cost_center': sale.cost_center,
                            'rate': sale.rate,
                            'account_currency': sale.account_currency
                        }
                        self.append('taxes', rows)
                    return True
    return False
        
        
def check_for_consignee_city(self) :
    if self.custom_consignee_city :
        sales_tax_list = frappe.get_all('Sales Taxes and Charges Template', 
                            filters = {
                                'custom_province' : self.custom_consignee_city
                            }
                        )
        if sales_tax_list :
            sales_tax_doc = frappe.get_doc('Sales Taxes and Charges Template', sales_tax_list[0].name)
            self.set('taxes_and_charges', sales_tax_doc.name)
            for sale in sales_tax_doc.taxes:
                rows = {
                    'charge_type': sale.charge_type,
                    'description': sale.description,
                    'account_head': sale.account_head,
                    'cost_center': sale.cost_center,
                    'rate': sale.rate,
                    'account_currency': sale.account_currency
                }
                self.append('taxes', rows)
            return True
        
        else :
            if frappe.db.exists('Territory', self.custom_consignee_city) :
                parent_territory = frappe.db.get_value('Territory', self.custom_consignee_city, 'parent_territory')
                sales_tax_list = frappe.get_all('Sales Taxes and Charges Template', 
                            filters = {
                                'custom_province' : parent_territory
                            }
                        )
                if sales_tax_list :
                    sales_tax_doc = frappe.get_doc('Sales Taxes and Charges Template', sales_tax_list[0].name)
                    self.set('taxes_and_charges', sales_tax_doc.name)
                    for sale in sales_tax_doc.taxes:
                        rows = {
                            'charge_type': sale.charge_type,
                            'description': sale.description,
                            'account_head': sale.account_head,
                            'cost_center': sale.cost_center,
                            'rate': sale.rate,
                            'account_currency': sale.account_currency
                        }
                        self.append('taxes', rows)
                    return True
    return False


def set_default_tax(self) :
    default_sales_tax = frappe.db.get_single_value('Manifest Setting Definition', 'default_sales_taxes_and_charges_template')
    if default_sales_tax :
        sales_tax_doc = frappe.get_doc('Sales Taxes and Charges Template', default_sales_tax)
        self.set('taxes_and_charges', sales_tax_doc.name)
        for sale in sales_tax_doc.taxes:
            rows = {
                'charge_type': sale.charge_type,
                'description': sale.description,
                'account_head': sale.account_head,
                'cost_center': sale.cost_center,
                'rate': sale.rate,
                'account_currency': sale.account_currency
            }
            self.append('taxes', rows)
    else :
        frappe.throw('Please set default sales tax template in Manifest Setting Definition')




def duty_and_tax_validation_on_submit(self, method):
    if self.custom_duty_and_taxes_invoice == 1 :
        if self.taxes_and_charges :
            self.taxes_and_charges = None
            self.taxes = []



############################ UMAIR WORK ############################
@frappe.whitelist()
def get_fuel_percentage_for_date(date_shipped):
    date = frappe.utils.getdate(date_shipped)
    records = frappe.get_all("Fuel Surcharge Percentage on Freight Amount",
        filters={
            "parent": "Additional Charges Page",
            "from_date": ["<=", date],
            "expiry_date": [">=", date]
        },
        fields=["fuel_surcharge_percentage_on_freight_amount"],
        order_by="from_date desc"
    )
    percentage = records[0]["fuel_surcharge_percentage_on_freight_amount"] if records else 0
    return percentage 