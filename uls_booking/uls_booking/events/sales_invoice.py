from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, cint, money_in_words,flt
import re
import logging


DEFAULT_CURRENCY = frappe.db.get_default("currency")

def get_sales_team_from_customer(customer_name):
    sales_team = frappe.get_all(
        "Sales Team",
        filters={"parenttype": "Customer", "parent": customer_name},
        fields=["sales_person", "allocated_percentage", "incentives"],
        order_by="idx"
    )
    if not sales_team:
        return []

    return sales_team

def check_type(shipment, logs):
    third_party_code = frappe.db.get_value(
        "R200000",
        {"shipment_number": shipment},
        "third_party_indicator_code"
    )

    if third_party_code is None:
        logs.append(f"No R200000 found for shipment {shipment}")
        third_party_code = "0"

    shipment_info = frappe.db.get_value(
        "Shipment Number",
        shipment,
        ["billing_term", "import__export"],
        as_dict=True
    )

    if not shipment_info:
        logs.append(f"No Shipment Number found for {shipment}")
        return False

    billing_term = (shipment_info.billing_term or "").strip().upper()
    imp_exp = (shipment_info.import__export or "").strip().upper()

    if imp_exp == "EXPORT":
        return billing_term == "F/C" or third_party_code != "0"

    if imp_exp == "IMPORT":
        return billing_term in {"P/P", "F/D"}

    return False

def get_frt_cust(icris_number, unassign, shipment_number, logs):
    """
    Determine customer from:
    1. ICRIS Account (original)
    2. R300000 → alternate_tracking_number_1 → Customer
    3. Unassigned ICRIS Account
    """
    
    alt_track_r3 = frappe.db.get_value("R300000", {"shipment_number": shipment_number}, "alternate_tracking_number_1")
    if alt_track_r3:
        cust_name = frappe.db.get_value(
            "Customer",
            {"disabled": 0, "custom_import_account_no": alt_track_r3},
            "name"
        )
        if cust_name:
            return cust_name    

    shipper_name = frappe.db.get_value("ICRIS Account", icris_number, "shipper_name")
    if shipper_name:
        return shipper_name

    shipper_name = frappe.db.get_value("ICRIS Account", unassign, "shipper_name")
    if shipper_name:
        logs.append(f"Customer not found from R300000.So using ICRIS Account: {unassign}")
        return shipper_name
    
    logs.append(f"No shipper_name in ICRIS Account: {icris_number}, checking R300000...")
    return None

def get_frt_cust_name(cust):
    cust_name = frappe.db.get_value(
            "Customer",
            {"name": cust},
            "customer_name"
        )
    if cust_name:
        return cust_name 

def get_frt_cust_account(cust):
    account_no = frappe.db.get_value(
            "Customer",
            {"name": cust},
            "custom_import_account_no"
        )
    if account_no:        
        return account_no 
    
def get_exchange_rate(from_currency, to_currency, date):
    filters = {"from_currency": from_currency, "to_currency": to_currency, "date": date}
    rate = frappe.get_list("Currency Exchange", filters=filters, fields=["exchange_rate"], order_by="date desc", limit_page_length=1)

    if not rate:
        filters["date"] = ["<", date]
        rate = frappe.get_list("Currency Exchange", filters=filters, fields=["exchange_rate"], order_by="date desc", limit_page_length=1)

    return rate[0].exchange_rate if rate else 0

def generate_invoice(self, method):
    logs = []
    imp_exp = "Export"
    sales_invoice = self
    if sales_invoice.custom_edit_customer:
        return
    
    if sales_invoice.custom_duty_and_taxes_invoice:
        reset_tax_fields(self)
        return


    if sales_invoice.custom_edit_items:
        edit_items = sales_invoice.get("items")

    if not sales_invoice.custom_compensation_invoices and not sales_invoice.custom_freight_invoices:
        if check_type(shipment_number, logs):
            sales_invoice.custom_compensation_invoices = True
            sales_invoice.custom_freight_invoices = False
        else:
            sales_invoice.custom_compensation_invoices = False
            sales_invoice.custom_freight_invoices = True
         



    shipment_number = sales_invoice.custom_shipment_number
    
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

    # export_billing_term = [term.billing_term for term in definition.export_and_import_conditions if term.export_check == 1]
    # import_billing_term = [term.billing_term for term in definition.export_and_import_conditions if  term.export_check == 0]
    
    for code in setting.surcharges_code_excl_and_incl:
        excluded_codes.append(code.excluded_codes)
        included_codes.append(code.included_codes)
    
    discounted_amount = discounted_amount + 1
    final_rate = 0
    tarif = 0
    final_discount_percentage = 0
    origin_country = None
    
    company = definition.default_company
    # customer = frappe.get_doc("Company",company)

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
    sales_invoice.conversion_rate = get_exchange_rate("USD", "PKR", shipped_date)
    is_export = False
    # is_export = sales_invoice.custom_shipper_country.upper() == definition.origin_country.upper()
    # imp_exp = "Export" if is_export else "Import"
    imp_or_exp = frappe.db.get_value("Shipment Number", sales_invoice.custom_shipment_number, "import__export")
    if imp_or_exp:
        if isinstance(imp_or_exp, list):
            imp_or_exp = imp_or_exp[0] if imp_or_exp else ""

        imp_or_exp = str(imp_or_exp).strip().lower()
        if imp_or_exp == "export":
            sales_invoice.custom_import__export_si = "Export"
            imp_exp = "Export"
            is_export = True
        elif imp_or_exp == "import":
            sales_invoice.custom_import__export_si = "Import"
            imp_exp = "Import"
    # print("before")
            
    




    if sales_invoice.custom_freight_invoices:
        
        if is_export:
            icris_number = sales_invoice.custom_shipper_number or definition.unassigned_icris_number
        else:
            icris_number = sales_invoice.custom_consignee_number or definition.unassigned_icris_number
        
        shipment_type = sales_invoice.custom_package_type or sales_invoice.custom_shipment_type
            
        try:
            icris_account = frappe.get_doc("ICRIS Account", icris_number)
        
        except frappe.DoesNotExistError:
            logs.append(f"No icris Account Found {icris_number}")
            if definition.unassigned_icris_number:
                icris_account = frappe.get_doc("ICRIS Account", definition.unassigned_icris_number)
        # print("frt")
        cust = get_frt_cust(icris_number, definition.unassigned_icris_number, shipment_number, logs)       
        sales_invoice.set("customer", cust)

        custName = get_frt_cust_name(cust)
        sales_invoice.set("customer_name", custName)

        accountNo = get_frt_cust_account(cust)
        sales_invoice.set("custom_account_no", accountNo)

        if is_export:
            if sales_invoice.custom_consignee_country:
                origin_country = sales_invoice.custom_consignee_country.capitalize()
                
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
                    # logs.append(f"No selling group Found thats why using Default Selling group")
                    selling_group = definition.default_selling_group
                if frappe.db.exists("Selling Rate Group", selling_group):
                    sales_invoice.set("custom_selling_rate_group", selling_group)
            full_tariff_flag = 0
            

            if selling_group == definition.default_selling_group:
                # Look for Full Tariff
                zones = frappe.get_list("Zone",
                                        filters = {"country" : origin_country , "is_single_country":1})
                flag = 0
                
                if zones:
                    sales_invoice.custom_zone = zones[0].name

                    full_tariff_query = """
                        SELECT name
                        FROM `tabFull Tariff`
                        WHERE country = %s
                        AND rate_type = %s
                        AND service_type = %s
                        AND package_type = %s
                        AND valid_from <= %s
                        AND expiry_date >= %s
                    """
                    if service_type and service_type[0].get("name"):
                        service_name = service_type[0].get("name")
                    else:
                        service_name = None

                    params = (origin_country, 'Selling', service_name, shipment_type, shipped_date, shipped_date)
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
                                    AND rate_type = %s
                                    AND service_type = %s
                                    AND package_type = %s
                                    AND valid_from <= %s
                                    AND expiry_date >= %s
                                """
                                if service_type and service_type[0].get("name"):
                                    service_name = service_type[0].get("name")
                                else:
                                    service_name = None
                                params = (zone_with_out_country, 'Selling', service_name, shipment_type, shipped_date, shipped_date)
                                full_tariff_name = frappe.db.sql(full_tariff_query, params, as_dict=True)

                                if full_tariff_name:
                                    full_tariff = frappe.get_doc("Full Tariff", full_tariff_name[0]["name"])
                                    full_tariff_flag = 1

                    except:
                        logs.append("No Full Tariff Found. Using Default Tariff")

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
                    
            if selling_group and full_tariff_flag == 0:

                zones = frappe.get_list("Zone",
                                        filters = {"country" : origin_country , "is_single_country":1})
                flag = 0
                if zones:
                    sales_invoice.custom_zone = zones[0].name
                    service_name = service_type[0].get("name") if service_type and service_type[0].get("name") else None
                    selling_rate_name = frappe.get_list("Selling Rate",
                        filters={
                            "country": origin_country,
                            "service_type": service_name,
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

                if flag == 1:
                    try:
                        countries = frappe.db.get_all("Country Names", filters={"countries":origin_country} , fields = ['parent'])
                        
                        if countries:
                            zone_with_out_country = countries[0].parent
                            if zone_with_out_country:
                                sales_invoice.custom_zone = zone_with_out_country
                                service_name = service_type[0].get("name") if service_type and service_type[0].get("name") else None
                                selling_rate_name = frappe.get_list("Selling Rate",
                                    filters={
                                        "zone": countries[0].parent,
                                        "service_type": service_name,
                                        "package_type": shipment_type,
                                        "rate_group": selling_group 
                                    }
                                )
                            
                                if selling_rate_name:        
                                    selling_rate = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                    
                                else :
                                    logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                    if definition.default_selling_rate:
                                        selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                        else:
                            logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                            if definition.default_selling_rate:
                                selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)    
                    except:
                        logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
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
        

        else:
            if sales_invoice.custom_shipper_country:
                origin_country = sales_invoice.custom_shipper_country.capitalize()
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
                # logs.append(f"No selling group Found thats why using Default Selling group")
                selling_group = definition.default_selling_group
            if frappe.db.exists("Selling Rate Group", selling_group):
                sales_invoice.set("custom_selling_rate_group", selling_group)
            full_tariff_flag = 0
            

            if selling_group == definition.default_selling_group:
                # Look for Full Tariff
                zones = frappe.get_list("Zone", filters={"country": origin_country, "is_single_country": 1})
                flag = 0
                if zones:
                    sales_invoice.custom_zone = zones[0].name

                    full_tariff_query = """
                        SELECT name
                        FROM `tabFull Tariff`
                        WHERE country = %s
                        AND rate_type = %s
                        AND service_type = %s
                        AND package_type = %s
                        AND valid_from <= %s
                        AND expiry_date >= %s
                    """
                    if service_type and service_type[0].get("name"):
                        service_name = service_type[0].get("name")
                    else:
                        service_name = None

                    params = (origin_country, 'Selling', service_name, shipment_type, shipped_date, shipped_date)
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
                                    AND rate_type = %s
                                    AND service_type = %s
                                    AND package_type = %s
                                    AND valid_from <= %s
                                    AND expiry_date >= %s
                                """
                                if service_type and service_type[0].get("name"):
                                    service_name = service_type[0].get("name")
                                else:
                                    service_name = None
                                params = (zone_with_out_country, 'Selling', service_name, shipment_type, shipped_date, shipped_date)
                                full_tariff_name = frappe.db.sql(full_tariff_query, params, as_dict=True)

                                if full_tariff_name:
                                    full_tariff = frappe.get_doc("Full Tariff", full_tariff_name[0]["name"])
                                    full_tariff_flag = 1

                    except:
                        logs.append("No Full Tariff Found. Using Default Tariff")
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
                    
            if selling_group and full_tariff_flag == 0:
                zones = frappe.get_list("Zone",
                                        filters = {"country" : origin_country , "is_single_country":1})
                
                flag = 0
                if zones:
                    sales_invoice.custom_zone = zones[0].name
                    service_name = service_type[0].get("name") if service_type and service_type[0].get("name") else None
                    selling_rate_name = frappe.get_list("Selling Rate",
                        filters={
                            "country": origin_country,
                            "service_type": service_name,
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
                            if zone_with_out_country:
                                sales_invoice.custom_zone = zone_with_out_country
                                service_name = service_type[0].get("name") if service_type and service_type[0].get("name") else None
                                selling_rate_name = frappe.get_list("Selling Rate",
                                    filters={
                                        "zone": zone_with_out_country,
                                        "service_type": service_name,
                                        "package_type": shipment_type,
                                        "rate_group": selling_group 
                                    }
                                )
                                if selling_rate_name:        
                                    selling_rate = frappe.get_doc("Selling Rate" , selling_rate_name[0].name)
                                    
                                else :
                                    logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                                    if definition.default_selling_rate:
                                        selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)

                        else:
                            logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                            if definition.default_selling_rate:
                                selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                    except:
                        logs.append(f"No Selling Rate Found Thats why using Default Selling Rate")
                        selling_rate = frappe.get_doc("Selling Rate",definition.default_selling_rate)
                my_weight = float(sales_invoice.custom_shipment_weight)
                if selling_rate :
                    flg = 0
                    last_row = {}
                    for row in selling_rate.package_rate:
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
                    if (surcharge_amount or 0) > 0:
                        amount = surcharge_amount
                else:
                    if amount is not None:
                        try:
                            amount = float(amount)
                        except (ValueError, TypeError):
                            amount = 0

                if code in exempt_code_list:
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
        additional_page = frappe.get_doc("Additional Charges Page")
        # FSCpercentage = frappe.db.get_single_value('Additional Charges Page','feul_surcharge_percentage_on_freight_amount')

        FSCpercentage = get_customer_fuel_percentage_for_date(shipped_date, sales_invoice.customer)

        if not FSCpercentage:
            FSCpercentage = additional_page.feul_surcharge_percentage_on_freight_amount
            for row in additional_page.fuel_surcharge_percentages_on_freight_amount:
                if row.expiry_date < shipped_date:  
                    latest_valid_percentage = row.fuel_surcharge_percentage_on_freight_amount
                
                if row.from_date <= shipped_date <= row.expiry_date:
                    FSCpercentage = row.fuel_surcharge_percentage_on_freight_amount
                    break
            if FSCpercentage == 0 and latest_valid_percentage != 0:
                FSCpercentage = latest_valid_percentage
        
        if FSCpercentage and final_rate:
                FSCcharges = (total_charges_incl_fuel + final_rate) * (FSCpercentage / 100 )
        shipmentbillingcheck = 0
        shipmentbillingamount = 0
        sbc_flag = 0
        if sales_invoice.customer:
            customer_doc = frappe.get_doc("Customer",sales_invoice.customer)
            # shipmentbillingcheck = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipping_bill_charges_applicable')
            shipmentbillingcheck = customer_doc.custom_shipping_bill_charges_applicable 
            if shipmentbillingcheck and shipment_type in sbc_included and shipment_type not in sbc_excluded:
                if shipmentbillingcheck and customer_doc.custom_shipping_billing_charges:
                        for row in customer_doc.custom_shipping_billing_charges:
                            # if float(row.from_weight) <= float(sales_invoice.custom_shipment_weight) <= float(row.to_weight):
                            if flt(row.from_weight) <= flt(sales_invoice.custom_shipment_weight) <= flt(row.to_weight) and row.import__export == imp_exp:
                                shipmentbillingamount = row.amount
                                sbc_flag = 1
                                break
                if imp_exp == "Export" and sbc_flag == 0:
                    # shipmentbillingamount = frappe.db.get_single_value('Additional Charges Page', 'export_amount_per_shipment')
                    shipmentbillingamount = additional_page.export_amount_per_shipment
                    
                elif imp_exp == "Import" and sbc_flag == 0:
                    # shipmentbillingamount = frappe.db.get_single_value('Additional Charges Page', 'import_amount_per_shipment')
                    shipmentbillingamount = additional_page.import_amount_per_shipment

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
        
        max_insured = 0
        
        if (declared_value or 0) > 0:
            # percent = frappe.db.get_single_value('Additional Charges Page', 'percentage_on_declare_value')
            # minimum_amount = frappe.db.get_single_value('Additional Charges Page', 'minimum_amount_for_declare_value')
            percent = additional_page.percentage_on_declare_value
            minimum_amount = additional_page.minimum_amount_for_declare_value
            result = declared_value * (percent / 100)
            max_insured = max(result , minimum_amount)
            
            if (max_insured or 0) > 0 and sales_invoice.custom_shipment_type == setting.insurance_shipment_type:
                rows = {'item_code': setting.insurance_charges, 'qty': '1', 'rate': max_insured}
                sales_invoice.append('items', rows)
        sales_invoice.custom_freight_charges = tarif
        amt = tarif - final_rate
        sales_invoice.discount_amount = round(amt, 2) or 0
        sales_invoice.base_discount_amount = (sales_invoice.discount_amount or 1)  * (sales_invoice.conversion_rate or 1)
        

        sales_invoice.custom_amount_after_discount = tarif - (sales_invoice.discount_amount or 0)
        
        
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
        
        # additional_surcharges_page = frappe.get_doc("Additional Charges Page")
        additional_surcharges_page = additional_page
        peak_amount = 0
        if additional_surcharges_page.peak_charges_duration_and_amount:    
            for row in additional_surcharges_page.peak_charges_duration_and_amount:
                if row.from_date <= shipped_date <= row.to_date:
                    if sales_invoice.custom_shipment_weight <= 0.5:
                        peak_amount = row.amount
                        break
                    elif (sales_invoice.custom_shipment_weight or 0) > 0.5:
                        peak_amount = sales_invoice.custom_shipment_weight * (row.amount)
        
        # exempt_peak_surcharge = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_peak_surcharge')
        exempt_peak_surcharge = customer_doc.custom_exempt_peak_surcharge
        if peak_amount and exempt_peak_surcharge != 1 :
            rows = {'item_code' : setting.peak_charges , 'qty' : '1' , 'rate' : peak_amount}
            sales_invoice.append('items' , rows)

        if sales_invoice.custom_edit_items:
            sales_invoice.items = edit_items
            freight_in_items = next(
                    (item_row.amount for item_row in sales_invoice.items if item_row.item_code == setting.freight_charges),0
                )
            sales_invoice.custom_freight_charges = freight_in_items






    elif sales_invoice.custom_compensation_invoices:
        export_compensation_amount = 0
        # exempt_customer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
        # if not exempt_customer:
        #     sales_invoice.taxes_and_charges = None
        #     sales_invoice.taxes = []
        for comp in definition.compensation_table:
            if sales_invoice.custom_billing_term.upper() == comp.shipment_billing_term.upper() and sales_invoice.custom_shipment_type.upper() == comp.shipping_billing_type.upper() and imp_exp.upper() == comp.case.upper():
                export_compensation_amount = comp.document_amount
                sales_invoice.append('items', {'item_code': setting.compensation_charges , 'qty': '1', 'rate': export_compensation_amount})
                break    

    
    # print("after")
    if sales_invoice.custom_edit_selling_percentage:
        final_discount_percentage = sales_invoice.custom_selling_percentage or 0
        sales_invoice.discount_amount = (sales_invoice.custom_freight_charges * final_discount_percentage / 100)
        sales_invoice.custom_amount_after_discount = sales_invoice.custom_freight_charges - sales_invoice.discount_amount
    else:
        sales_invoice.custom_selling_percentage = final_discount_percentage
        sales_invoice.custom_inserted = 1

        
    log_name = frappe.db.get_value("Sales Invoice Logs", {"shipment_number": shipment_number}, "name")
    log_doc = frappe.get_doc("Sales Invoice Logs", log_name) if log_name else frappe.new_doc("Sales Invoice Logs")

    if not sales_invoice.items:
        
        log_doc.set("sales_invoice_status", "Failed")
        logs.append(f"No Items shipment number {shipment_number}, icris number {icris_number}")
        log_text = "\n".join(logs)
        if sales_invoice.custom_compensation_invoices:
            log_doc.set(
                'logs',
                f"No Items shipment number {shipment_number}, icris number {icris_number}\n"
                f"Shipment Billing Term: {sales_invoice.custom_billing_term}, "
                f"Shipment Type: {sales_invoice.custom_shipment_type}, "
                f"Imp/Exp: {imp_exp}"
            )
        else:
            log_doc.set("logs", log_text)
        
        if frappe.db.exists("Shipment Number", shipment_number):
            log_doc.set("shipment_number" , shipment_number)
        
        if frappe.db.exists("ICRIS Account", icris_number):
            log_doc.set("icris_number" , icris_number)
        log_doc.save()
        return
    if sales_invoice.custom_edit_selling_percentage:
        customer = sales_invoice.customer
        date_shipped = sales_invoice.custom_date_shipped

        # 1️⃣ Try customer-specific percentage
        per = get_customer_fuel_percentage_for_date(date_shipped, customer)

        # 2️⃣ If not found, use global setting
        if not per:
            per = get_fuel_percentage_for_date(date_shipped)

        for row in sales_invoice.items:
            if row.item_code == setting.fuel_charges:
                base_amount = (
                    sales_invoice.custom_amount_after_discount
                    + sales_invoice.custom_total_surcharges_incl_fuel
                )
                row.rate = (base_amount * per) / 100

    
    discounted_amount = discounted_amount - 1
    get_sales_tax(sales_invoice, logs)
    log_text = "\n".join(logs)
    sales_invoice.set_missing_values()
    sales_team = get_sales_team_from_customer(sales_invoice.customer)
    sales_invoice.set("sales_team", [])
    for member in sales_team:
        sales_invoice.append("sales_team", member)
    
    ############################################################################################
    exempt_case = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_exempt_gst')
    if exempt_case:
        # sales_invoice.taxes_and_charges = None
        # sales_invoice.taxes = []
        sales_invoice.taxes = []
        sales_invoice.taxes_and_charges = None

        sales_invoice.total_taxes_and_charges = 0
        sales_invoice.base_total_taxes_and_charges = 0

        if hasattr(sales_invoice, "other_charges_calculation") and sales_invoice.other_charges_calculation:
            sales_invoice.other_charges_calculation = ''
        sales_invoice.grand_total = sales_invoice.total
        sales_invoice.base_grand_total = sales_invoice.base_total

        sales_invoice.rounded_total = sales_invoice.grand_total
        sales_invoice.base_rounded_total = sales_invoice.base_grand_total
        sales_invoice.outstanding_amount = sales_invoice.grand_total
        sales_invoice.base_outstanding_amount = sales_invoice.base_grand_total

        sales_invoice.in_words = money_in_words(sales_invoice.rounded_total, self.currency)
        sales_invoice.base_in_words = money_in_words(sales_invoice.base_total, DEFAULT_CURRENCY)
    ############################################################################################
    sales_invoice.calculate_taxes_and_totals()
    if (sales_invoice.discount_amount or 0) > 0:
        disc_per = (sales_invoice.discount_amount / sales_invoice.total) * 100 if (sales_invoice.total or 0) > 0 else 0
        sales_invoice.additional_discount_percentage = 0
        sales_invoice.set("additional_discount_percentage", disc_per)
        sales_invoice.calculate_taxes_and_totals()
    sales_invoice.in_words = money_in_words(sales_invoice.rounded_total, sales_invoice.currency)
    sales_invoice.base_in_words = money_in_words(sales_invoice.base_rounded_total, DEFAULT_CURRENCY)
    
    
    if logs:
        if frappe.db.exists("Shipment Number", shipment_number):
            log_doc.set("shipment_number" , shipment_number)
        if frappe.db.exists("ICRIS Account", icris_number):
            log_doc.set("icris_number" , icris_number)
        log_doc.set("logs", log_text)
        log_doc.save()
    frappe.db.commit()
    # print("si end")
    

def get_sales_tax(self, logs=None):
    if self.custom_freight_invoices == 1:
        self.set('taxes_and_charges', None)
        self.taxes = []
        ret = check_for_shipper_city(self)
        if not ret :
            ret1 = check_for_consignee_city(self)
            if not ret1 :
                set_default_tax(self)
                if logs:
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
        
        
def check_for_consignee_city(self):
    if self.custom_consignee_city:
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



def before_delete(self, method):
    frappe.db.sql("""
        DELETE FROM `tabDispute Invoice Number`
        WHERE customers_sales_invoice = %(invoice)s
    """, {"invoice": self.name})

    frappe.db.sql("""
        DELETE FROM `tabSales Invoice Logs`
        WHERE sales_invoice = %(invoice)s
    """, {"invoice": self.name})




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

@frappe.whitelist()
def get_customer_fuel_percentage_for_date(date_shipped, customer):
    date = frappe.utils.getdate(date_shipped)
    records = frappe.get_all("Fuel Surcharge Percentage on Freight Amount",
        filters={
            "parent": customer,
            "parenttype": "Customer",
            "from_date": ["<=", date],
            "expiry_date": [">=", date]
        },
        fields=["fuel_surcharge_percentage_on_freight_amount"],
        order_by="from_date desc"
    )
    percentage = records[0]["fuel_surcharge_percentage_on_freight_amount"] if records else 0
    return percentage 

@frappe.whitelist()
def get_money_in_words(amount, currency=None):
    return money_in_words(amount, currency)



def reset_tax_fields(self):
    exempt = frappe.db.get_value("Customer", self.customer, "custom_exempt_gst")
    if exempt:
        self.taxes = []
        self.taxes_and_charges = None

        self.total_taxes_and_charges = 0
        self.base_total_taxes_and_charges = 0

        if hasattr(self, "other_charges_calculation") and self.other_charges_calculation:
            self.other_charges_calculation = ''

        # self.total = self.net_total
        # self.base_total = self.base_net_total
        self.grand_total = self.total
        self.base_grand_total = self.base_total

        self.rounded_total = self.grand_total
        self.base_rounded_total = self.base_grand_total
        self.outstanding_amount = self.grand_total
        self.base_outstanding_amount = self.base_grand_total

        self.in_words = money_in_words(self.rounded_total, self.currency)
        self.base_in_words = money_in_words(self.base_rounded_total, DEFAULT_CURRENCY)
    else:
        if not self.taxes_and_charges and not self.taxes:
            get_sales_tax(self)
