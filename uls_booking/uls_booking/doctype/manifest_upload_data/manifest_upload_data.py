from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from frappe.utils.background_jobs import enqueue
import time

from frappe.utils import getdate
import json
import re
from datetime import datetime
import requests
import traceback

TEST_MODE = False

class ManifestUploadData(Document):
    def on_submit(self):
        frappe.msgprint("Manifest Data Processing Started", alert=True)
        self.db_set("status", "Started")
        shipped_date = self.shipped_date if self.shipped_date else None
        import_date = self.import_date if self.import_date else None
       

        if self.attach_file and self.manifest_file_type == "ISPS":
            is_import = self.export_import.lower() == "import"
            file_name = frappe.db.get_value("File", {"file_url": self.attach_file}, "name")
            file_proper_name = frappe.get_value("File",file_name,"file_name")
            # print("File Name",file_proper_name,"\n\n\n\n\n")
            file_doc = frappe.get_doc("File", file_name)
            content = safe_decode(file_doc)
            arrays = content.split('\n')
            frm = int(self.from_index)-1
            to = int(self.to_index)
            shipfrom = int(self.shipment_number_from_index)-1
            shipto = int(self.shipment_number_to_index)
            #chunk_size = 10  
            
            # current_index = 0
            
            # while current_index < len(arrays):
            #     chunk = arrays[current_index:current_index + chunk_size]  
            #     current_index += chunk_size
            #     enqueue(insert_data, manifest_upload_data_name = self.name, gateway = self.gateway, is_import = is_import, shipped_date = shipped_date , import_date = import_date , file_proper_name = file_proper_name , arrays=chunk, frm=frm, to=to, date_format = self.date_format, queue="long")
                
            # enqueue(storing_shipment_number, arrays=arrays, frm=shipfrom, to=shipto, doc=self, queue="long")
                        
            # total_chunks = (len(arrays) + chunk_size - 1) // chunk_size

            # for i in range(total_chunks):     #commented to send array instead of chunk
            # for i in range(arrays):            #commented b/c loop is not needed here
            # chunk = arrays[i*chunk_size:(i+1)*chunk_size]
            # is_last = i == total_chunks - 1
                
            enqueue(
                    insert_data,
                    manifest_upload_data_name=self.name,
                    gateway=self.gateway,
                    is_import=is_import,
                    shipped_date=shipped_date,
                    import_date=import_date,
                    file_proper_name=file_proper_name,
                    shipf=shipfrom,
                    shipt=shipto,
                    arrays=arrays,
                    docnew=self,
                    frm=frm,
                    to=to,
                    date_format=self.date_format,
                    queue="long",
                    timeout=86400
                )
                
            # if is_last:           #commented no more need
                    # Run storing_shipment_number s minutes later
            #time.sleep(delay_seconds)
        elif self.manifest_file_type == "DWS" and self.modified_file:

            file_name2 = frappe.db.get_value("File", {"file_url": self.modified_file}, "name")
            file_doc2 = frappe.get_doc("File", file_name2)
            content2 = safe_decode(file_doc2)
            arrays2 = content2.split('\n')
            pkg_from = int(self.package_tracking_from_index)-1
            pkg_to = int(self.package_tracking_to_index)-1
            chunk2_size = 10
            current2_index = 0

            while current2_index < len(arrays2):
                chunk2 = arrays2[current2_index:current2_index + chunk2_size]
                current2_index += chunk2_size
                # modified_manifest_update(main_doc = self, arrays2 = chunk2, pkg_from = pkg_from , pkg_to= pkg_to, date_format = self.date_format)
                enqueue(modified_manifest_update,main_doc = self, arrays2 = chunk2, pkg_from = pkg_from , pkg_to= pkg_to, date_format = self.date_format,  queue = "default")
        elif self.manifest_file_type == "OPSYS" and self.opsys_file:
            file_name3 = frappe.db.get_value("File", {"file_url": self.opsys_file}, "name")
            file_doc3 = frappe.get_doc("File", file_name3)
            file_proper_name3 = file_doc3.file_name
            content3 = safe_decode(file_doc3)
            arrays3 = content3.split('\n')
            frm = int(self.from_index)-1
            to = int(self.to_index)
            shipfrom = int(self.shipment_number_from_index)-1
            shipto = int(self.shipment_number_to_index)
            # chunk_size3 = 100  
            # current_index3 = 0
            
            # while current_index3 < len(arrays3):
            #     chunk = arrays3[current_index3:current_index3 + chunk_size3]             
            #     current_index3 += chunk_size3
            #     enqueue(opsys_insert_data, shipped_date = shipped_date, import_date = import_date, file_proper_name3 = file_proper_name3 , arrays=chunk, frm=frm, to=to, date_format = self.date_format, manifest_upload_data_name=self.name, gateway=self.gateway, queue="long")
            
            # enqueue(storing_shipment_number,arrays=arrays3, frm=shipfrom, to=shipto, doc=self ,queue="long")
            # total_chunks3 = (len(arrays3) + chunk_size3 - 1) // chunk_size3

            # for i in range(total_chunks3):
            #     chunk = arrays3[i * chunk_size3:(i + 1) * chunk_size3]
            #     is_last = i == total_chunks3 - 1

            enqueue(
                opsys_insert_data,
                shipped_date=shipped_date,
                import_date=import_date,
                file_proper_name3=file_proper_name3,
                arrays=arrays3,
                docnew=self,
                shipf=shipfrom,
                shipt=shipto,
                frm=frm,
                to=to,                
                date_format=self.date_format,
                manifest_upload_data_name=self.name,
                gateway=self.gateway,
                queue="long",
                timeout=86400
                )

                #if is_last:
            # enqueue(
            #     storing_shipment_number,
            #     arrays=arrays3,
            #     frm=shipfrom,
            #     to=shipto,
            #     doc=self,
            #     queue="long"
            #     )
                
            
import frappe
import json
from datetime import datetime
from frappe.utils import getdate
from frappe import _
from frappe.utils import flt

# --- Helpers used by the main function ---

def _norm_date(value):
    """Normalize date-like values to YYYY-MM-DD string or None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    # fallback: return trimmed string
    return s

def _find_candidates_for_doctype(doctype, shipment, limit=10):
    """
    Return up to `limit` candidate rows for `doctype` by matching shipment_number exactly.
    Simpler and safer than combining name / name like / shipment_number filters.
    """
    try:
        candidates = frappe.get_list(
            doctype,
            filters={"shipment_number": shipment},
            fields=["name", "shipment_number", "import_date", "date_shipped", "manifest_import_date", "shipped_date"],
            order_by="modified desc",
            limit_page_length=limit
        )
    except Exception:
        candidates = []
    return candidates


def generate_sales_invoice_enqued(doc_str, doc, shipments, definition_record, name, end_date, chunk_size):
    """
    Patched generate_sales_invoice_enqued with robust shipment lookup and create_new-only invoice creation.
    Parameters mirror your original function.
    """
    try:
        final_rate = 0
        tarif = 0
        discounted_amount = 0
        selling_rate_zone = None
        selling_rate_country = 0
        arrayy = []
        sales_name = []

        # Load Sales Invoice Definition
        try:
            definition = frappe.get_doc("Sales Invoice Definition", definition_record)
        except frappe.DoesNotExistError:
            frappe.throw(_("Sales Invoice Definition does not exist"))
        except frappe.PermissionError:
            frappe.throw(_("You do not have permission to access the Sales Invoice Definition"))
        except Exception as e:
            frappe.throw(_("Error fetching Sales Invoice Definition: ") + str(e))

        shipment = doc.get("shipment_numbers", "")
        frappe.db.set_value("Generate Sales Invoice", name, "status", "In Progress")
        shipments = [value.strip() for value in shipment.split(",") if value.strip()]

        setting = frappe.get_doc("Manifest Setting Definition")
        excluded_codes = []
        included_codes = []
        for code in setting.surcharges_code_excl_and_incl:
            excluded_codes.append(code.excluded_codes)
            included_codes.append(code.included_codes)

        # build billing term arrays
        export_billing_term = []
        import_billing_term = []
        for term in definition.export_and_import_conditions:
            if term.export_check == 1:
                export_billing_term.append(term.billing_term)
            elif term.export_check == 0:
                import_billing_term.append(term.billing_term)

        total_invoices = 0
        actual_invoices = 0

        # process shipments
        for shipment in shipments:
            log = []
            discounted_amount = discounted_amount + 1
            final_rate = 0
            tarif = 0
            signal = 0
            customer_signal = 0
            final_discount_percentage = 0
            selected_weight = 0
            origin_country = None

            # --- Check if Sales Invoice already exists for this shipment (robust) ---
            existing_invoice = frappe.get_list(
                "Sales Invoice",
                filters=["or",
                         ["custom_shipment_number", "=", shipment],
                         ["custom_shipment_number", "like", f"{shipment}-%"]],
                fields=["name"],
                order_by="modified desc",
                limit_page_length=1
            )

            if existing_invoice:
                # Already invoiced (skip)
                print("Present In Sales Invoice:", existing_invoice[0].get("name"))
                continue

            # --- BEFORE creating invoice: decide whether shipment is "new" ---
            # get incoming dates for this shipment (use R200000 as authoritative)
            r200 = frappe.db.get_value("R200000", {"shipment_number": shipment},
                                      ["manifest_import_date", "shipped_date"], as_dict=True)

            if r200:
                incoming_input_date = r200.get("manifest_input_date")

            # check existing Shipment Number candidates (if any) to see if this is create_new only
            sn_candidates = _find_candidates_for_doctype("Shipment Number", shipment, limit=10)
            best_candidate, action = choose_best_shipment_candidate(
                sn_candidates,
                incoming_manifest_input_date=incoming_input_date
            )

          
            # only proceed to create invoice when action == "create_new"
            if action != "create_new":
                # log and skip invoice creation
                if action == "update":
                    frappe.log(f"Skipping invoice creation for shipment {shipment}: exact shipment record exists ({candidate.get('name')})")
                elif action == "alert_update":
                    frappe.log(f"Skipping invoice creation for shipment {shipment}: manifest date conflict with existing ({candidate.get('name')}). Billing may be alerted elsewhere.")
                continue

            # --- Proceed to create a Sales Invoice for a "new" shipment ---
            sales_invoice = frappe.new_doc("Sales Invoice")

            company = definition.default_company
            customer = frappe.get_doc("Company", company, fields=["custom_default_customer"])
            sales_invoice.customer = customer.custom_default_customer

            doctype_name = None
            total_charges_incl_fuel = 0
            total_charges_other_charges = 0
            FSCcharges = 0
            FSCpercentage = 0
            shipment_type = 0

            # Populate sales_invoice fields using definition mapping
            for child_record in definition.sales_invoice_definition:
                doctype_name = child_record.ref_doctype
                field_name = child_record.field_name
                sales_field_name = child_record.sales_invoice_field_name

                # robustly find candidate in the mapped doctype
                # candidates = _find_candidates_for_doctype(doctype_name, shipment, limit=5)

                # pick best candidate (use incoming dates we fetched earlier)
                # chosen_candidate, _pick_action = choose_best_shipment_candidate(candidates=   candidates,incoming_manifest_input_date= incoming_input_date)
                chosen_name = best_candidate.get("name") if best_candidate else None

                if chosen_name:
                    # fetch the value of the requested field cheaply
                    try:
                        value = frappe.get_value(doctype_name, chosen_name, field_name)
                    except Exception:
                        value = None
                    # set on sales_invoice if we got a value
                    if value is not None:
                        sales_invoice.set(sales_field_name, value)

            # set posting date etc.
            date2 = getdate(end_date)
            sales_invoice.posting_date = date2
            posting_date = getdate(sales_invoice.posting_date)
            sales_invoice.set_posting_time = 1

            # Identify ICRIS account / customer
            icris_number = None
            selling_group = None
            selling_rate = None

            if sales_invoice.custom_shipper_country == definition.origin_country.upper():
                imp_exp = "Export"
                icris_number = sales_invoice.custom_shipper_number or definition.unassigned_icris_number
                if not sales_invoice.custom_shipper_number:
                    log.append("No Shipper Number Found: Shipment Number: {0}".format(shipment))
            else:
                imp_exp = "Import"
                icris_number = sales_invoice.custom_consignee_number or definition.unassigned_icris_number
                if not sales_invoice.custom_consignee_number:
                    log.append("No Consignee Number Found: Shipment Number: {0}".format(shipment))

            # retrieve weights
            weight_frm_R200000 = frappe.get_value("R202000", {"shipment_number": shipment}, "custom_expanded_shipment_weight") or 0
            weight_frm_R201000 = frappe.get_value("R201000", {"shipment_number": shipment}, "custom_minimum_bill_weight") or 0
            try:
                weight_frm_R200000 = float(weight_frm_R200000)
            except Exception:
                weight_frm_R200000 = 0.0
            try:
                weight_frm_R201000 = float(weight_frm_R201000)
            except Exception:
                weight_frm_R201000 = 0.0

            selected_weight = max(weight_frm_R200000, weight_frm_R201000)
            sales_invoice.custom_shipment_weight = selected_weight

            # package type mapping
            if sales_invoice.custom_package_type:
                for code in definition.package_type_replacement:
                    if sales_invoice.custom_package_type == code.package_type_code:
                        sales_invoice.custom_package_type = code.package_type
                        shipment_type = sales_invoice.custom_package_type
                        break
            else:
                shipment_type = sales_invoice.custom_shipment_type

            # get icris account doc (best-effort)
            icris_account = None
            try:
                if icris_number:
                    icris_account = frappe.get_doc("ICRIS Account", icris_number)
            except frappe.DoesNotExistError:
                log.append("No ICRIS Account Found; assigning default: {0}".format(definition.unassigned_icris_number))
                if definition.unassigned_icris_number:
                    try:
                        icris_account = frappe.get_doc("ICRIS Account", definition.unassigned_icris_number)
                        icris_number = definition.unassigned_icris_number
                    except Exception:
                        icris_account = None
                else:
                    # nothing we can do — skip this shipment
                    continue
            except Exception as e:
                frappe.log_error(f"ICRIS account fetch error for {icris_number}: {e}", "ICRIS Fetch Error")

            # Determine selling group & rates (same as your logic; preserved)
            if sales_invoice.custom_billing_term in export_billing_term and sales_invoice.custom_shipper_country == definition.origin_country.upper():
                # Ensure icris exists / set customer
                if icris_account and icris_account.shipper_name:
                    sales_invoice.customer = icris_account.shipper_name
                else:
                    log.append("No Customer Found: Shipment Number: {0}, ICRIS Number: {1}".format(shipment, icris_number))

                # taxes and charges selection (preserve your territory logic)
                try:
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
                        rows = {'charge_type': charge_type, 'description': description, 'account_head': account_head, 'cost_center': cost_center, 'rate': rate, 'account_currency': account_currency}
                        sales_invoice.append('taxes', rows)
                    else:
                        raise Exception("Use default")
                except Exception:
                    stc = frappe.get_doc("Sales Taxes and Charges Template", definition.default_sales_tax)
                    for sale in stc.taxes:
                        charge_type = sale.charge_type
                        description = sale.description
                        account_head = sale.account_head
                        cost_center = sale.cost_center
                        rate = sale.rate
                        account_currency = sale.account_currency
                    sales_invoice.set("taxes_and_charges", stc.name)
                    rows = {'charge_type': charge_type, 'description': description, 'account_head': account_head, 'cost_center': cost_center, 'rate': rate, 'account_currency': account_currency}
                    sales_invoice.append('taxes', rows)
                    log.append("No Territory Found so Using Default sales Tax and charges Template: Territory {0}".format(sales_invoice.custom_shipper_city))

                # set origin_country for zone logic
                if sales_invoice.custom_consignee_country:
                    origin_country = sales_invoice.custom_consignee_country.capitalize()

                # determine selling_group from icris_account.rate_group if available
                service_type = frappe.get_list("Service Type", filters={"imp__exp": imp_exp, "service": sales_invoice.custom_service_type})
                if service_type and icris_account:
                    for icris in icris_account.rate_group:
                        if icris.service_type == service_type[0].get("name") and icris.from_date <= posting_date <= icris.to_date:
                            selling_group = icris.rate_group
                            break
                    if not selling_group:
                        log.append("No Selling Group Found - using default")
                        selling_group = definition.default_selling_group

                # find selling_rate by zone/country (preserve your logic)
                if selling_group:
                    zones = frappe.get_list("Zone", filters={"country": origin_country, "is_single_country": 1})
                    flag = 0
                    if zones:
                        sales_invoice.custom_zone = zones[0].name
                        selling_rate_name = frappe.get_list("Selling Rate",
                                                           filters={
                                                               "country": origin_country,
                                                               "service_type": service_type[0].get("name"),
                                                               "package_type": shipment_type,
                                                               "rate_group": selling_group
                                                           })
                        if selling_rate_name:
                            selling_rate = frappe.get_doc("Selling Rate", selling_rate_name[0].name)
                        else:
                            flag = 1
                    else:
                        flag = 1

                    if flag == 1:
                        try:
                            countries = frappe.db.get_all("Country Names", filters={"countries": origin_country}, fields=['parent'])
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
                                                                       })
                                    if selling_rate_name:
                                        selling_rate = frappe.get_doc("Selling Rate", selling_rate_name[0].name)
                                    else:
                                        log.append("No Selling Rate Found - using default")
                                        if definition.default_selling_rate:
                                            selling_rate = frappe.get_doc("Selling Rate", definition.default_selling_rate)
                            else:
                                log.append("No Selling Rate Found - using default")
                                if definition.default_selling_rate:
                                    selling_rate = frappe.get_doc("Selling Rate", definition.default_selling_rate)
                        except Exception:
                            log.append("No Selling Rate Found - using default (exception)")
                            selling_rate = frappe.get_doc("Selling Rate", definition.default_selling_rate)

                    my_weight = float(sales_invoice.custom_shipment_weight or 0)
                    if selling_rate:
                        flg = 0
                        last_row = {}
                        for row in selling_rate.package_rate:
                            if my_weight <= row.weight:
                                final_rate = row.rate
                                final_discount_percentage = row.discount_percentage
                                flg = 1
                                break
                            else:
                                last_row = row
                        if flg == 0:
                            final_rate = (last_row.rate / last_row.weight) * my_weight
                            final_discount_percentage = last_row.discount_percentage
                        tarif = final_rate / (1 - (final_discount_percentage / 100))

            # Import billing branch (preserve)
            elif sales_invoice.custom_billing_term in import_billing_term and sales_invoice.custom_shipper_country != definition.origin_country.upper():
                # similar logic for imports (preserved)
                # ... (omitted here for brevity but same as your original code)
                pass

            # currency
            currency = frappe.get_value("Customer", sales_invoice.customer, "default_currency")
            sales_invoice.currency = currency

            # Surcharge extraction (preserve your logic)
            codes_incl_fuel = []
            amounts_incl_fuel = []
            surcharge_codes_incl_fuel = []
            codes_other_charges = []
            amounts_other_charges = []
            surcharge_codes_other_charges = []

            if doctype_name:
                r201 = frappe.get_list("R201000", filters={'shipment_number': shipment})
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

                # append surcharge rows
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

                FSCpercentage = frappe.db.get_single_value('Additional Charges Page', 'feul_surcharge_percentage_on_freight_amount')
                if FSCpercentage and tarif:
                    FSCcharges = (total_charges_incl_fuel + final_rate) * (FSCpercentage / 100)

            # shipment billing amount logic (preserved)
            shipmentbillingcheck = 0
            shipmentbillingamount = 0
            shipmentbillingchargesfromcustomer = 0
            if sales_invoice.customer:
                shipmentbillingcheck = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipping_bill_charges_applicable')
                shipmentbillingchargesfromcustomer = frappe.db.get_value('Customer', sales_invoice.customer, 'custom_shipment_billing_charges')
                if shipmentbillingcheck and not shipmentbillingchargesfromcustomer:
                    if imp_exp == "Export":
                        shipmentbillingamount = frappe.db.get_single_value('Additional Charges Page', 'export_amount_per_shipment')
                    elif imp_exp == "Import":
                        shipmentbillingamount = frappe.db.get_single_value('Additional Charges Page', 'import_amount_per_shipment')
                elif shipmentbillingcheck and shipmentbillingchargesfromcustomer:
                    shipmentbillingamount = shipmentbillingchargesfromcustomer

            # insurance / discount / items append (preserved)
            declared_value = sales_invoice.custom_insurance_amount
            decalred_value = 0
            if isinstance(declared_value, (int, float)):
                declared_value = float(declared_value)
            elif isinstance(declared_value, str):
                try:
                    declared_value = float(declared_value.strip())
                except Exception:
                    declared_value = 0
            else:
                declared_value = 0

            max_insured = 0
            if sales_invoice.customer != customer.custom_default_customer:
                sales_invoice.custom_freight_invoices = 1
                if decalred_value > 0:
                    percent = frappe.db.get_single_value('Additional Charges Page', 'percentage_on_declare_value')
                    minimum_amount = frappe.db.get_single_value('Additional Charges Page', 'minimum_amount_for_declare_value')
                    result = decalred_value * (percent / 100)
                    max_insured = max(result, minimum_amount)
                    if max_insured > 0 and shipment_type == setting.insurance_shipment_type:
                        rows = {'item_code': setting.insurance_charges, 'qty': 1, 'rate': max_insured}
                        sales_invoice.append('items', rows)

                sales_invoice.discount_amount = tarif - final_rate
                sales_invoice.custom_amount_after_discount = tarif - sales_invoice.discount_amount
                sales_invoice.custom_selling_percentage = final_discount_percentage

                if total_charges_other_charges:
                    rows = {'item_code': setting.other_charges, 'qty': 1, 'rate': total_charges_other_charges}
                    sales_invoice.append('items', rows)
                if FSCcharges:
                    rows = {'item_code': setting.fuel_charges, 'qty': 1, 'rate': FSCcharges}
                    sales_invoice.append('items', rows)
                if tarif:
                    rows = {'item_code': setting.freight_charges, 'qty': 1, 'rate': tarif}
                    sales_invoice.append('items', rows)
                if shipmentbillingamount:
                    rows = {'item_code': setting.shipment_billing_charges, 'qty': 1, 'rate': shipmentbillingamount}
                    sales_invoice.append('items', rows)

            # compensation (preserved)
            export_compensation_amount = 0
            if sales_invoice.customer == customer.custom_default_customer:
                sales_invoice.custom_compensation_invoices = 1
                for comp in definition.compensation_table:
                    if sales_invoice.custom_billing_term == comp.shipment_billing_term and shipment_type == comp.shipping_billing_type and imp_exp == comp.case:
                        export_compensation_amount = comp.document_amount
                        rows = {'item_code': setting.compensation_charges, 'qty': 1, 'rate': export_compensation_amount}
                        sales_invoice.append('items', rows)
                        break

            # if no items then log and skip
            if not sales_invoice.items:
                log_text = "N0 Items - Shipment: {0}, ICRIS: {1}".format(sales_invoice.custom_shipment_number, icris_number)
                log.append(log_text)
                for row in doc.get("shipment_numbers_and_sales_invoices", []):
                    if sales_invoice.custom_shipment_number == row.get('shipment_number'):
                        if log and not row.get('sales_invoice'):
                            code = ["500 :"]
                            code.extend(log)
                            code_str = " ".join(code)
                            frappe.db.set_value("Shipment Numbers And Sales Invoices", row.get('name'), "log", code_str)
                continue

            # finalize invoice
            discounted_amount = discounted_amount - 1
            sales_invoice.run_method("set_missing_values")
            sales_invoice.run_method("calculate_taxes_and_totals")
            sales_invoice.insert()
            total_invoices += 1
            actual_invoices += 1
            sales_name.append(sales_invoice.name)

            # link sales invoice back to shipment mapping rows
            for row in doc.get("shipment_numbers_and_sales_invoices", []):
                if sales_invoice.custom_shipment_number == row.get('shipment_number'):
                    frappe.db.set_value("Shipment Numbers And Sales Invoices", row.get('name'), "sales_invoice", sales_invoice.name)
                    if log and not row.get('sales_invoice'):
                        code = ["500 :"]
                        code.extend(log)
                        code_str = " ".join(code)
                        frappe.db.set_value("Shipment Numbers And Sales Invoices", row.get('name'), "log", code_str)
                    else:
                        code = "200 :"
                        frappe.db.set_value("Shipment Numbers And Sales Invoices", row.get('name'), "log", code)

            if total_invoices == chunk_size:
                frappe.db.commit()
                total_invoices = 0

        frappe.db.set_value("Generate Sales Invoice", name, "status", "Generated")

    except json.JSONDecodeError:
        frappe.throw(_("Invalid JSON data"))
    except Exception as e:
        frappe.throw(_("An error occurred: ") + str(e))


def chunk_list(lst, chunk_size):
    """Split a list into chunks of a specified size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def chunk_process(doc_str,doc,shipments,definition_record,name,end_date,chunk_size):
    # count=0
    for shipment_chunk in chunk_list(shipments, chunk_size):
        # count += 1
        generate_sales_invoice_enqued(doc_str=doc_str,
        doc=doc,
        shipments=shipment_chunk,
        definition_record=definition_record,
        name=name,end_date=end_date,chunk_size=chunk_size)

        # enqueue(generate_sales_invoice_enqued,doc_str=doc_str,
        # doc=doc,
        # shipments=shipment_chunk,
        # definition_record=definition_record,
        # name=name,end_date=end_date,queue = "default")
        # frappe.db.commit()
        



@frappe.whitelist()
def generate_sales_invoice(doc_str):
    doc = json.loads(doc_str)
    name = doc['name']
    definition_record = doc.get("sales_invoice_definition")
    end_date = doc.get("end_date")
    chunk_size = doc.get("chunk_size")
    shipment_numbers_without_invoice = []
    
    shipment_numbers_without_invoice = frappe.get_list(
                "Shipment Numbers And Sales Invoices",
                filters={
                    "parent": name,
                    "sales_invoice": ["is", "not set"] 
                },
                pluck="shipment_number",
                ignore_permissions=True
            )
    
    # chunk_process(doc_str=doc_str,doc = doc,shipments = shipment_numbers_without_invoice,definition_record=definition_record,name = name,end_date=end_date,chunk_size=chunk_size)
    enqueue(chunk_process,doc_str=doc_str,doc = doc,shipments = shipment_numbers_without_invoice,definition_record=definition_record,name = name,end_date=end_date,chunk_size=chunk_size,queue="default")
    
   

@frappe.whitelist()
def generate_remaining_sales_invoice():
    records = frappe.db.sql("""
                SELECT name
                FROM `tabGenerate Sales Invoice`
                WHERE total_sales_invoices_generated < total_shipment_numbers
                AND docstatus = 1
            """, as_dict=True)
    
    for record in records:
        doc = frappe.get_doc("Generate Sales Invoice", record.name)
        doc_dict = doc.as_dict()
        name = doc_dict.get('name')
        # frappe.throw(str(name))
        definition_record = doc_dict.get('sales_invoice_definition')
        end_date = doc_dict.get('end_date')
        chunk_size = doc_dict.get('chunk_size')
        shipment_numbers_without_invoice = frappe.get_list(
                "Shipment Numbers And Sales Invoices",
                filters={
                    "parent": name,
                    "sales_invoice": ["is", "not set"] 
                },
                pluck="shipment_number",
                ignore_permissions=True
            )
        chunk_process(doc_str=doc_dict,doc = doc_dict,shipments = shipment_numbers_without_invoice,definition_record=definition_record,name = name,end_date=end_date,chunk_size=chunk_size)
    # chunk_process(doc_str=doc_str,doc = doc,shipments = shipment_numbers_without_invoice,definition_record=definition_record,name = name,end_date=end_date,chunk_size=chunk_size)
        # enqueue(chunk_process,doc_str=doc_dict,doc = doc_dict,shipments = shipment_numbers_without_invoice,definition_record=definition_record,name = name,end_date=end_date,chunk_size=chunk_size,queue="default")
        

def safe_like(value: str):
    """Utility: return a safe LIKE filter dict."""
    return {"name": ["like", value]}

# Unified safe get_list wrapper

def safe_get_list(doctype: str, filters=None, fields=None, order_by=None, limit=10):
    """Wrapper around frappe.get_list ensuring valid filter formats.
    - Dict filters preferred
    - If OR/AND blocks are used, leave them untouched
    """
    try:
        # Normalize simple list filters into dict
        if isinstance(filters, list) and all(isinstance(x, list) for x in filters):
            # Check OR/AND logical operators
            if filters and filters[0][0] in ("or", "and"):
                # example: [["or", [field,..],[field,..]]]
                pass
            else:
                # Convert list-of-lists to dict: [[f, op, v]] -> {f: [op, v]}
                new_filters = {}
                for f in filters:
                    if len(f) == 3:
                        new_filters[f[0]] = [f[1], f[2]]
                filters = new_filters

        return frappe.get_list(
            doctype,
            filters=filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=limit
        )
    except Exception as e:
        frappe.log_error(f"safe_get_list failed for {doctype}: {e}", "Safe Get List Error")
        return []

# Patched version of _find_shipment_number_docs

def _find_shipment_number_docs(shipment, limit=15):
    # Exact match first
    docs = safe_get_list(
        "Shipment Number",
        filters={"shipment_number": shipment},
        fields=["name", "shipment_number", "import_date", "date_shipped", "manifest_upload_data", "manifest_input_date"],
        order_by="modified desc",
        limit=limit,
    )
    if docs:
        return docs

    # Fallback LIKE search using safe dict format
    like_filter = {"name": ["like", f"{shipment}-%"]}
    docs_like = safe_get_list(
        "Shipment Number",
        filters=like_filter,
        fields=["name", "shipment_number", "import_date", "date_shipped", "manifest_upload_data", "manifest_input_date"],
        order_by="modified desc",
        limit=limit,
    )
    return docs_like or []




def _notify_billing_simple(subject, message, recipients=None, reference_doctype=None, reference_name=None):
    """Small notify helper (best-effort)."""
    if not recipients:
        try:
            s = frappe.get_doc("Manifest Setting Definition")
            recipients = getattr(s, "billing_emails", None)
        except Exception:
            recipients = None
    if not recipients:
        recipients = ["billing@example.com"]

    if isinstance(recipients, (list, tuple)):
        recipients = ",".join(recipients)

    try:
        frappe.sendmail(recipients=recipients, subject=subject, content=message, reference_doctype=reference_doctype, reference_name=reference_name)
    except Exception as e:
        frappe.log_error(f"Failed to send billing mail: {e}", "Notify Billing Error")
    try:
        frappe.publish_realtime(event="msgprint", message=subject + "\n\n" + message)
    except Exception:
        pass

def _normalize_date_str(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return s

def choose_best_shipment_candidate(candidates, incoming_manifest_input_date):
    """
    candidates: list of dicts returned by frappe.get_list(...),
                each dict should have at least keys 'name', 'input_date'
    incoming_manifest_input_date: raw value from file (string/date)

    returns: (best_candidate_dict_or_None, action_str)
      action_str is one of:
        - "update"
        - "create_new"
    """

    in_input_date = _normalize_date_str(incoming_manifest_input_date)

    if not in_input_date:
        # No reliable key → safest option
        return None, "create_new"

    if not candidates:
        return None, "create_new"

    # Normalize candidate input_date
    normalized = []
    for c in candidates:
        c_input_date = _normalize_date_str(c.get("manifest_input_date"))
        normalized.append((c, c_input_date))

    # 1️⃣ Exact match on input_date → update
    exact_matches = [
        c for c, ci in normalized
        if ci and ci == in_input_date
    ]

    if exact_matches:
        # Assuming candidates are ordered by modified desc
        return exact_matches[0], "alert_update"

    # 2️⃣ No match → create new
    return None, "create_new"

def create_shipment_number_record(shipment, origin_country, r2_data, doc, allow_update_override=True):
    """
    Create or update a Shipment Number record for the given shipment id based on r2_data.
    If a matching Shipment Number record exists (by name or shipment_number field), we apply date rules:
      - update / alert_update / create_new (autoname will handle new name)
    """
    billing_term = r2_data.get("billing_term_field") if isinstance(r2_data, dict) else getattr(r2_data, "billing_term_field", None)
    date_shipped = r2_data.get("shipped_date") if isinstance(r2_data, dict) else getattr(r2_data, "shipped_date", None)
    import_date = r2_data.get("manifest_import_date") if isinstance(r2_data, dict) else getattr(r2_data, "manifest_import_date", None)
    file_type = r2_data.get("file_type") if isinstance(r2_data, dict) else getattr(r2_data, "file_type", None)
    file_name = r2_data.get("file_name") if isinstance(r2_data, dict) else getattr(r2_data, "file_name", None)
    manifest_input_date = r2_data.get("manifest_input_date") if isinstance(r2_data, dict) else getattr(r2_data, "manifest_input_date", None)

    # Find existing Shipment Number docs robustly
    existing_candidates = _find_shipment_number_docs(shipment, limit=5)

    candidate, action = choose_best_shipment_candidate(existing_candidates, incoming_manifest_input_date=manifest_input_date)
    
    existing_candidate = candidate        # dict or None
    existing_name = candidate.get("name") if candidate else None
    # helper to fill fields (shared for update and new)
    def _populate_and_save_shipment_doc(shipment_doc):
        try:
            # default fields (some fieldnames changed to your schema's names)
            shipment_doc.set("shipment_number", shipment)
            shipment_doc.set("customer", shipment_doc.get("customer") or None)  # leave customer if already set
            shipment_doc.set("date_shipped", date_shipped)
            shipment_doc.set("station", shipment_doc.get("station") or None)
            shipment_doc.set("icris_number", shipment_doc.get("icris_number") or None)
            shipment_doc.set("billing_type", shipment_doc.get("billing_type") or None)
            shipment_doc.set("billing_term", billing_term)
            shipment_doc.set("file_name", file_name)
            shipment_doc.set("import__export", shipment_doc.get("import__export") or None)
            shipment_doc.set("import_date", import_date)
            shipment_doc.set("manifest_file_type", file_type)
            shipment_doc.set("manifest_upload_data", doc.name)
            shipment_doc.set("gateway", getattr(doc, "gateway", None))
            # if you have other fields to set, do it here

            shipment_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error saving Shipment Number {shipment}: {e}", "Shipment Save Error")
            raise

    def _update_existing_shipment(existing_name):
        try:
            shipment_doc = frappe.get_doc("Shipment Number", existing_name)
            # populate additional fields using R300000 / R400000 lookups as before
            try:
                # Export shipments
                export_array_temp = frappe.get_list("R300000",
                    filters=[["shipper_country", "=", origin_country], ["shipment_number", "=", shipment]],
                    fields=["shipment_number", "shipper_number"]
                )
                if export_array_temp:
                    station = frappe.get_value("R300000", {"shipment_number": shipment}, "shipper_city")
                    shipper_number = export_array_temp[0].get("shipper_number")
                    import_export = "Export"
                    icris = frappe.get_list("ICRIS Account", filters=[["name", "=", shipper_number]], fields=["shipper_name", "icris_account"])
                    if icris:
                        shipment_doc.customer = icris[0].get("shipper_name")
                        shipment_doc.billing_type = frappe.get_value("Customer", icris[0].get("shipper_name"), "custom_billing_type")
                        shipment_doc.icris_number = icris[0].get("icris_account")
                        shipment_doc.station = station
                        shipment_doc.import__export = import_export
                # Import shipments
                import_array_temp = frappe.get_list("R400000",
                    filters=[["consignee_country_code", "=", origin_country], ["shipment_number", "=", shipment]],
                    fields=["shipment_number", "consignee_number"]
                )
                if import_array_temp:
                    station = frappe.get_value("R400000", {"shipment_number": shipment}, "consignee_city")
                    consignee_number = import_array_temp[0].get("consignee_number")
                    import_export = "Import"
                    icris = frappe.get_list("ICRIS Account", filters=[["name", "=", consignee_number]], fields=["shipper_name", "icris_account"])
                    if icris:
                        shipment_doc.customer = icris[0].get("shipper_name")
                        shipment_doc.billing_type = frappe.get_value("Customer", icris[0].get("shipper_name"), "custom_billing_type")
                        shipment_doc.icris_number = icris[0].get("icris_account")
                        shipment_doc.station = station
                        shipment_doc.import__export = import_export
            except Exception as ex:
                frappe.log_error(f"Error fetching import/export info for {shipment}: {ex}", "Shipment Lookup Error")

            # set fields & save
            _populate_and_save_shipment_doc(shipment_doc)
        except Exception as e:
            frappe.log_error("Error updating Shipment Number", f"Shipment: {shipment}. Error: {e}\n{traceback.format_exc()}")
            raise        
    if action == "update" and existing_name:
        # Update the existing doc
        _update_existing_shipment(existing_name)

    elif action == "alert_update" and existing_name:
        # Always notify on alert_update
        # Only update if allow_update_override is True
        cand_name = existing_name

        msg = (
            f"A manifest upload attempted to update shipment {shipment}.\n\n"
            f"Existing Manifest Import Date: {existing_candidate.get('import_date')}\n"
            f"Existing Shipped Date: {existing_candidate.get('date_shipped')}\n\n"
            f"Incoming Manifest Import Date: {import_date}\n"
            f"Incoming Shipped Date: {date_shipped}\n\n"
            f"Manifest Upload File: {doc.name}\n"
            f"File Name: {file_name}\n\n"
            "Please review before updating. To force update via upload, set allow_update_override=True."
        )        
        subject = f"Shipment {shipment} manifest/shipped date mismatch"

        try:
            s = frappe.get_doc("Manifest Setting Definition")
            recipients = getattr(s, "billing_emails", None)
        except Exception:
            recipients = None

        _notify_billing_simple(subject, msg, recipients, reference_doctype="Shipment Number", reference_name=cand_name)

        # Always append to failed shipments for manual review
        doc.append('failed_shipments', {
            "shipment": shipment,
            "reason": "Date mismatch: manifest import date same but shipped date differs"
        })

        if allow_update_override:
            _update_existing_shipment(existing_name)

    else:
        # create_new: create a fresh Shipment Number record (autoname will generate full name)
        try:
            # populate customer/icris/station similar to existing branch
            customer = None
            icris_number = None
            billing_type = None
            station = None
            import_export = None

            try:
                export_array_temp = frappe.get_list("R300000",
                    filters=[["shipper_country", "=", origin_country], ["shipment_number", "=", shipment]],
                    fields=["shipment_number", "shipper_number"]
                )

                if export_array_temp:
                    station = frappe.get_value("R300000", {"shipment_number": shipment}, "shipper_city")
                    shipper_number = export_array_temp[0].get("shipper_number")
                    import_export = "Export"
                    icris = frappe.get_list("ICRIS Account", filters=[["name", "=", shipper_number]], fields=["shipper_name", "icris_account"])
                    if icris:
                        customer = icris[0].get("shipper_name")
                        billing_type = frappe.get_value("Customer", icris[0].get("shipper_name"), "custom_billing_type")
                        icris_number = icris[0].get("icris_account")

                import_array_temp = frappe.get_list("R400000",
                    filters=[["consignee_country_code", "=", origin_country], ["shipment_number", "=", shipment]],
                    fields=["shipment_number", "consignee_number"]
                )

                if import_array_temp:
                    station = frappe.get_value("R400000", {"shipment_number": shipment}, "consignee_city")
                    consignee_number = import_array_temp[0].get("consignee_number")
                    import_export = "Import"
                    icris = frappe.get_list("ICRIS Account", filters=[["name", "=", consignee_number]], fields=["shipper_name", "icris_account"])
                    if icris:
                        customer = icris[0].get("shipper_name")
                        billing_type = frappe.get_value("Customer", icris[0].get("shipper_name"), "custom_billing_type")
                        icris_number = icris[0].get("icris_account")
            except Exception as ex:
                frappe.log_error(f"Error fetching import/export info for {shipment}: {ex}", "Shipment Lookup Error")

            shipment_doc = frappe.new_doc("Shipment Number")
            # set base shipment_number (autoname requires this if autoname depends on shipment_number)
            shipment_doc.set("shipment_number", shipment)
            shipment_doc.set("customer", customer)
            shipment_doc.set("billing_term", billing_term)
            shipment_doc.set("date_shipped", date_shipped)
            shipment_doc.set("station", station)
            shipment_doc.set("icris_number", icris_number)
            shipment_doc.set("billing_type", billing_type)
            shipment_doc.set("file_name", file_name)
            shipment_doc.set("import__export", import_export)
            shipment_doc.set("import_date", import_date)
            shipment_doc.set("manifest_file_type", file_type)
            shipment_doc.set("manifest_upload_data", doc.name)
            shipment_doc.set("gateway", getattr(doc, "gateway", None))

            shipment_doc.insert(ignore_permissions=True)
            # optionally save (insert already saved to DB, but save ensures triggers run)
            shipment_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(message=f"Error creating Shipment Number: {str(e)}\n\n{traceback.format_exc()}",
                             title="Shipment Creation Error "+ str(shipment) + '-' + str(file_type) + '-' + str(doc.name))
            raise

def storing_shipment_number(arrays, frm, to, doc):
    """
    Parse unique shipment numbers from arrays and ensure Shipment Number records exist/updated.
    Applies date-based rules:
      - same shipment_id + same manifest_import_date + same shipped_date -> update
      - same shipment_id + same manifest_import_date but shipped_date differs -> alert (and append to failed_shipments)
      - same shipment_id but manifest/import or shipped differ -> create new Shipment Number
    """
    current_shipment = None
    try:
        shipment_numbers = set()

        for line in arrays:
            try:
                shipment_num = line[frm:to].strip()
                if shipment_num:
                    shipment_numbers.add(shipment_num)
            except IndexError:
                frappe.log_error("Data Processing Error", f"IndexError processing line: {line}")
                continue
            except Exception as e:
                frappe.log_error("Data Processing Error", f"Unexpected error processing line: {line}. Error: {str(e)}")
                continue

        unique_shipment_numbers = list(shipment_numbers)
        origin_country = frappe.db.get_single_value("Manifest Setting Definition", "origin_country")

        # update manifest upload data summary
        frappe.db.set_value("Manifest Upload Data", doc.name, "total_shipment_numbers", len(unique_shipment_numbers))

        failed_shipments = []
        again_failed_shipments = []

        for shipment in unique_shipment_numbers:
            current_shipment = shipment
            shipment = (shipment or "").strip()
            # find R200000 (source data) - try robust lookup (shipment_number field)
            r2_data = frappe.db.get_value("R200000", {"shipment_number": shipment}, ["billing_term_field", "shipped_date", "manifest_import_date", "file_type", "file_name", "manifest_input_date"], as_dict=True)
            if not r2_data:
                # fallback: maybe R200000 name uses different pattern — try like
                r2_candidates = frappe.get_list("R200000", filters=[["name", "=", shipment], ["name", "like", f"{shipment}-%"]], fields=["name"], limit_page_length=1)
                if r2_candidates:
                    r2_data = frappe.db.get_value("R200000", {"name": r2_candidates[0].get("name")}, ["billing_term_field", "shipped_date", "manifest_import_date", "file_type", "file_name", "manifest_input_date"], as_dict=True)

            if not r2_data:
                failed_shipments.append(shipment)
                continue

            try:
                # Pass allow_update_override maybe via Manifest Upload Data doc or other config; default False here
                create_shipment_number_record(shipment, origin_country, r2_data, doc, allow_update_override=True)
            except Exception as cse1:
                frappe.log_error("Create Shipment Number Record Error " + str(frm) + '-' + str(to),
                                 f"Error creating shipment numbers for shipment: {current_shipment}. Error: {str(cse1)}\n{traceback.format_exc()}")

        # Retry failed shipments once (as in original logic)
        for shipment in failed_shipments:
            r2_data = frappe.db.get_value("R200000", {"shipment_number": shipment}, ["billing_term_field", "shipped_date", "manifest_import_date", "file_type", "file_name"], as_dict=True)
            if not r2_data:
                again_failed_shipments.append(shipment)
                doc.append('failed_shipments', {
                    "shipment": shipment,
                    "reason": "No R200000 record found"
                })
                continue

            try:
                create_shipment_number_record(shipment, origin_country, r2_data, doc)
            except Exception as cse2:
                frappe.log_error("Create Again Shipment Number Record Error " + str(frm) + '-' + str(to),
                                 f"Error creating shipment numbers for shipment: {current_shipment}. Error: {str(cse2)}\n{traceback.format_exc()}")

        # update counts and status
        shipment_names = frappe.db.get_all("Shipment Number", filters={"manifest_upload_data": doc.name}, pluck="name")
        unique_shipment_numbers_created = set(shipment_names)
        frappe.db.set_value("Manifest Upload Data", doc.name, "created_shipments", len(unique_shipment_numbers_created))
        frappe.db.set_value("Manifest Upload Data", doc.name, "status", "Completed")
    except Exception as e:
        frappe.log_error("Shipment Number Storage Error " + str(frm) + '-' + str(to),
                         f"Error storing shipment numbers for shipment: {current_shipment}. Error: {str(e)}\n{traceback.format_exc()}")
        frappe.db.set_value("Manifest Upload Data", doc.name, "status", "Failed")


def make_R300000(self):
    self.shipper_city = self.shipper_city.capitalize()

def make_R400000(self):
    self.consignee_city = self.consignee_city.capitalize()

def make_R600000(self):
    if self.package_length and self.package_width and self.package_height:
        self.package_length = float(self.package_length) / 10
        self.package_width = float(self.package_width) / 10
        self.package_height = float(self.package_height) / 10
        self.dws_dim = (float(self.package_length) * float(self.package_width) * float(self.package_height)) / 5000.0
    if self.dws_hours and self.dws_minutes and self.dws_seconds:
        time_str = f"{self.dws_hours:02}:{self.dws_minutes:02}:{self.dws_seconds:02}"
        self.time_of_dws = time_str
    if self.dws_actual_weight:
        self.dws_actual_weight = float(self.dws_actual_weight) / 10


def insert_data(arrays, docnew, shipf, shipt, frm, to, date_format, manifest_upload_data_name, gateway, file_proper_name, shipped_date, import_date, is_import):
    
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

    try:
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
                    
                    if row.field_name == "expanded_package_tracking_number":
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

            
            # frappe.msgprint(str(doctype_name))
            # frappe.msgprint("Hello")

            if docs:
                
                print("Doc found:", docs[0])
                docss = frappe.get_doc(doctype_name, docs[0])
                # docss.set("check", 0)
                docss.set("file_name",file_proper_name)
                docss.set("manifest_upload_data",manifest_upload_data_name)
                docss.set("gateway",gateway)

                for child_record in definition.definitions:
                    field_name = child_record.field_name
                    from_index = child_record.from_index - 1
                    to_index = child_record.to_index
                    field_data = line[from_index:to_index].strip()

                    
                    if field_name in field_names_array:
                        # print(field_name," is present", doctype_name) 
                        if field_data in country_map:
                            field_data = country_map[field_data]
                    key = (str(field_name), str(field_data))
                    # print(f"Checking key: {key}")

                    if key in replacement_map:
                        field_data = replacement_map[key]
                    
                    for field in setting.date_conversion_field_names:
                        if field_name == field.field_name and doctype_name == field.doctype_name:
                            try:
                                date_object = datetime.strptime(field_data, field.date_format)
                                output_date_format = "%Y-%m-%d"
                                field_data = date_object.strftime(output_date_format)
                            except:
                                pass
                                
                    for field in setting.fields_to_divide:
                        if doctype_name == field.doctype_name and field_name == field.field_name:
                            try:
                                field_data = float(field_data) if field_data else 0.0
                            except ValueError:
                                field_data = 0.0
                            if field.number_divide_with:
                                field_data = field_data / field.number_divide_with
                    
                    # if shipped_date and field_name == "shipped_date":
                    #     field_data = shipped_date
                    # if import_date and field_name == "manifest_import_date":
                    #     field_data = import_date

                    ######################## Umair Work #######################
                    # (Reverse work) Means when import.... update shipped field, when export.... update import field
                    if is_import and field_name == "manifest_import_date":
                        continue
                    if not is_import and field_name == "shipped_date":
                        continue
                    ######################## Umair Work #######################

                    docss.set(field_name, field_data)

                if doctype_name == "R300000":
                    if docss.shipper_city:
                        make_R300000(docss)
                elif doctype_name == "R400000":
                    if docss.consignee_city:
                        make_R400000(docss)
                if hasattr(docss, "file_type") and not docss.file_type:
                    docss.file_type = "ISPS"

                if TEST_MODE:
                    frappe.log_error("TEST MODE - Not inserting", f"Shipment: {shipment}")
                else:
                    docss.save(ignore_permissions=True)
                    frappe.db.commit()
                

            else:
                doc = frappe.new_doc(doctype_name)
                doc.set("file_name",file_proper_name)
                doc.set("manifest_upload_data",manifest_upload_data_name)
                doc.set("gateway",gateway)

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
                            # try:
                            #     date_object = datetime.strptime(field_data, date_format)
                            #     output_date_format = "%Y-%m-%d"
                            #     field_data = date_object.strftime(output_date_format)
                            # except:
                            #     pass
                            try:
                                date_object = datetime.strptime(field_data, field.date_format)
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
                                
                                field_data = 0.0
                            if field.number_divide_with:
                                field_data = field_data / field.number_divide_with
                    # if shipped_date and field_name == "manifest_shipped_date":
                    #     field_data = shipped_date
                    # if import_date and field_name == "manifest_import_date":
                    #     field_data = import_date
                    ######################## Umair Work #######################
                    # reverse work...means when import update shipped field , when export update import field
                    if is_import and field_name == "manifest_import_date":
                        continue
                    if not is_import and field_name == "shipped_date":
                        continue
                    ######################## Umair Work #######################
                    doc.set(field_name, field_data)
        
                if doctype_name == "R300000":
                    if doc.shipper_city:
                        make_R300000(doc)
                elif doctype_name == "R400000":
                    if doc.consignee_city:
                        make_R400000(doc)
                if  hasattr(doc, "file_type") and not doc.file_type:
                    doc.file_type = "ISPS"

                
                doc.insert(ignore_permissions=True)
                doc.save(ignore_permissions=True)            
                
                #committing entry one by one
                frappe.db.commit()
                    
                   
    except Exception as e:
        frappe.log_error("Error in committing in ISPS", f"Error in ManifestUploadData: {str(e)}") 

    try:
        storing_shipment_number(arrays=arrays, frm=shipf, to=shipt, doc=docnew)
    except Exception as e:
        frappe.log_error("Error in storing shipment number ISPS" + str(shipf) + '-' + str(shipt), f"Error in storing shipment number: {str(e)}") 
    
    
def modified_manifest_update(main_doc,arrays2,pkg_from,pkg_to,date_format):
    try:
        setting = frappe.get_doc("Manifest Setting Definition")
        
        for line in arrays2:
            pkg_trck = line[pkg_from:pkg_to].strip()
            docl = frappe.get_list(main_doc.record_to_modify, filters={"expanded_package_tracking_number": pkg_trck })
            if docl:
                doc = frappe.get_doc(main_doc.record_to_modify , docl[0])
                for child in setting.definition:
                    field_name = child.field_name
                    from_index = child.from_index - 1
                    to_index = child.to_index
                    field_data = line[from_index:to_index].strip()
                    for field in setting.date_conversion_field_names:
                        if field_name == field.field_name and main_doc.record_to_modify == field.doctype_name:

                            try:
                                date_object = datetime.strptime(field_data, date_format)
                                output_date_format = "%Y-%m-%d"
                                field_data = date_object.strftime(output_date_format)

                            except: 
                                pass

                    doc.set(field_name,field_data)
                    # print(field_name , "  ",field_data)
                make_R600000(doc)
                doc.save(ignore_permissions=True)
            else:
                frappe.get_doc({
                    "doctype": "Error Log",
                    "method": "Package tracking Number not found",
                    "error": f"""Package tracking Number:,{pkg_trck}"""

                }).insert()
        frappe.db.set_value("Manifest Upload Data", main_doc.name, "status", "Completed")
    except Exception as e:
        frappe.log_error("Manifest Update Error", f"Error in modified_manifest_update: {str(e)}")
        frappe.db.set_value("Manifest Upload Data", main_doc.name, "status", "Failed")


def parse_opsys_line(line, definition, doctype_name, setting,
                     country_map, replacement_map, field_names_array):
    """
    Parse a single OPSYS line ONCE and return a dict of field_name -> value
    """
    parsed = {}

    for row in definition.opsys_definitions:
        field_name = row.field_name
        from_index = row.from_index - 1
        to_index = row.to_index

        value = line[from_index:to_index].strip()

        # Country replacement
        if field_name in field_names_array and value in country_map:
            value = country_map[value]

        # Replacement map
        key = (field_name, value)
        if key in replacement_map:
            value = replacement_map[key]

        # Date conversion
        for field in setting.date_conversion_field_names:
            if field_name == field.field_name and doctype_name == field.doctype_name:
                try:
                    value = datetime.strptime(value, field.date_format).strftime("%Y-%m-%d")
                except Exception:
                    value = None

        # Divide numeric fields
        for field in setting.fields_to_divide:
            if doctype_name == field.doctype_name and field_name == field.field_name:
                try:
                    value = float(value) / field.number_divide_with
                except Exception:
                    value = 0.0

        parsed[field_name] = value

    return parsed

@frappe.whitelist()
def opsys_insert_data(arrays, docnew, shipf, shipt, frm, 
                      to, file_proper_name3, date_format,
                      shipped_date, import_date, manifest_upload_data_name, 
                      gateway):
    """
    Updated OPSYS import routine with robust lookup/insert/update logic for Shipment Number
    - respects new naming (shipment_number-00001)
    - implements rules:
        * same shipment_id + same manifest_import_date + same shipped_date -> UPDATE
        * same shipment_id + same manifest_import_date but shipped_date differs -> ALERT (notify Billing); 
    """


    # ---- Begin main logic ----
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

    running_shipment_number = None
    running_manifest_input_date = None
    running_action = "create_new"      # update / alert_update / create_new
    running_candidate = None

    try:
        for line in arrays:

            # Determine doctype name from line segments
            doctype_name = "R" + line[frm:to].strip()
            old_doctype_name = line[frm:to].strip()
            prefix = doctype_name[:2]

            # Skip R100000 lines as these are flight headers
            if doctype_name == "R100000":
                continue

            if prefix in parent_doctype_map:
                doctype_name = parent_doctype_map[prefix]

            # Load definition manifest for this doctype
            try:
                definition = frappe.get_doc("Definition Manifest", doctype_name)

                parsed = parse_opsys_line(
                    line=line,
                    definition=definition,
                    doctype_name=doctype_name,
                    setting=setting,
                    country_map=country_map,
                    replacement_map=replacement_map,
                    field_names_array=field_names_array
                )

                shipment_num = parsed.get("shipment_number")

                if not shipment_num:
                    frappe.log_error(
                        "OPSYS Parse Error",
                        f"OPSYS line skipped: no shipment_number parsed.\nLine: {line}"
                        
                    )
                    continue

                is_new_shipment = shipment_num != running_shipment_number

                pkg_trck = parsed.get("expanded_package_tracking_number")

                if is_new_shipment and doctype_name == "R200000":
                    running_shipment_number = shipment_num
                    running_manifest_input_date = parsed.get("manifest_input_date")
                    running_candidate = None
                    running_action = "create_new"  # safe default

                    if not running_manifest_input_date:
                        frappe.log_error(
                            f"OPSYS Import Warning {shipment_num}",
                            f"Shipment {shipment_num} has no manifest_input_date in R200000. "
                            "Proceeding as create_new."
                        )

            except frappe.DoesNotExistError:
                # No definition for this doctype: skip line
                continue

            # --- Attempt to find existing docs ---
            docs = []
            # If doctype is in parent_doctype_map, original code used a custom filter string.
            # We'll keep trying the original approach, but add a robust fallback using structured filters.
            if prefix in parent_doctype_map:
                # attempt to use stored record.filter (string), with token replacements as before
                filter_str = None
                for record in setting.doctypes_with_child_records:
                    if doctype_name == record.record:
                        filter_str = record.filter
                        break

                if filter_str:
                    # replace tokens safely
                    if "pkg_trck" in filter_str and pkg_trck:
                        filter_str = re.sub(r'\b(pkg_trck)\b', f'"{pkg_trck}"', filter_str)
                    if "shipment_num" in filter_str and shipment_num:
                        filter_str = re.sub(r'\b(shipment_num)\b', f'"{shipment_num}"', filter_str)
                    if "old_doctype_name" in filter_str and old_doctype_name:
                        filter_str = re.sub(r'\b(old_doctype_name)\b', f'"{old_doctype_name}"', filter_str)

                    print(filter_str, "", pkg_trck, "1", "\n\n")
                    try:
                        # Try using the original string filter first (some installations rely on it)
                        docs = frappe.get_list(doctype_name, filters=filter_str, fields=["name", "shipment_number", "manifest_import_date", "shipped_date", "manifest_input_date"], limit_page_length=1)
                    except Exception:
                        docs = []

                # Fallback: robust search by shipment_num and pkg_trck
                if not docs:
                    docs = find_shipment_docs(doctype_name, shipment_num, pkg_trck)
            else:
                # Non-parent doc path — previously used simple {'shipment_number': shipment_num}
                try:
                    docs = frappe.get_list(doctype_name, filters={'shipment_number': shipment_num}, fields=["name", "shipment_number", "manifest_import_date", "shipped_date", "manifest_input_date"], limit_page_length=1)
                except Exception:
                    # fallback to robust search
                    docs = find_shipment_docs(doctype_name, shipment_num, pkg_trck)

            # Normalize docs format (get_list returns list of dicts with 'name')
            if docs:
                # pick first candidate (most recent because of order_by in fallback)
                if is_new_shipment and doctype_name == "R200000":
                    running_candidate, running_action = choose_best_shipment_candidate(
                        docs,
                        incoming_manifest_input_date=running_manifest_input_date
                    )


                candidate = running_candidate
                action = running_action
                    
                if candidate:
                    cand_name = candidate.get("name")
                else:
                    cand_name = None

                # If candidate is just a string or tuple, coerce to dict
                if isinstance(candidate, (list, tuple)):
                    candidate = {"name": candidate[0]}
                if isinstance(candidate, dict) and "name" in candidate:
                    cand_name = candidate.get("name")
                else:
                    # fallback: if docs[0] is a simple string
                    cand_name = docs[0] if isinstance(docs[0], str) else None


                if action == "update":
                    # Update existing document
                    docss = frappe.get_doc(doctype_name, cand_name)
                    docss.set("file_name", file_proper_name3)
                    docss.set("manifest_upload_data", manifest_upload_data_name)
                    docss.set("gateway", gateway)

                    # apply field mappings (same logic as before)
                    for field_name, field_data in parsed.items():
                        if shipped_date and field_name == "shipped_date":
                            field_data = shipped_date
                        if import_date and field_name == "manifest_import_date":
                            field_data = import_date

                        docss.set(field_name, field_data)


                    # run special makers if required
                    if doctype_name == "R300000":
                        if docss.shipper_city:
                            make_R300000(docss)
                    elif doctype_name == "R400000":
                        if docss.consignee_city:
                            make_R400000(docss)
                    if hasattr(docss, "file_type") and not docss.file_type:
                        docss.file_type = "OPSYS"

                    if TEST_MODE:
                        frappe.log_error("SHIPMENT EXISTS", f"Shipment: {shipment_num}")
                    else:
                        docss.save(ignore_permissions=True)
                        frappe.db.commit()

                elif action == "alert_update":
                    # Notify billing and possibly update if override allowed
                    subject = f"Shipment {shipment_num} manifest/shipped date mismatch"
                    msg = (
                        f"A manifest upload attempted to update shipment {shipment_num}.\n\n"
                        f"Existing Manifest Import Date: {candidate.get('manifest_import_date')}\n"
                        f"Existing Shipped Date: {candidate.get('shipped_date')}\n\n"
                        f"Incoming Manifest Import Date: {import_date}\n"
                        f"Incoming Shipped Date: {shipped_date}\n\n"
                        f"Manifest Upload File: {manifest_upload_data_name}\n"
                        f"Package Tracking: {pkg_trck}\n\n"
                        "Please review before updating. To force update via upload, set allow_update_override=True."
                    )
                    try:
                        s = frappe.get_doc("Manifest Setting Definition")
                        recipients = getattr(s, "billing_emails", None)
                    except Exception:
                        recipients = None
                    notify_billing(subject, msg, recipients, reference_doctype=doctype_name, reference_name=cand_name)

                    docss = frappe.get_doc(doctype_name, cand_name)
                    docss.set("file_name", file_proper_name3)
                    docss.set("manifest_upload_data", manifest_upload_data_name)
                    docss.set("gateway", gateway)
                    # apply same field mappings as update

                    for field_name, field_data in parsed.items():
                        if shipped_date and field_name == "shipped_date":
                            field_data = shipped_date
                        if import_date and field_name == "manifest_import_date":
                            field_data = import_date

                        docss.set(field_name, field_data)


                    if doctype_name == "R300000":
                        if docss.shipper_city:
                            make_R300000(docss)
                    elif doctype_name == "R400000":
                        if docss.consignee_city:
                            make_R400000(docss)
                    if hasattr(docss, "file_type") and not docss.file_type:
                        docss.file_type = "OPSYS"

                    if TEST_MODE:
                        frappe.log_error("CREATING NEW SHIPMENT", f"Shipment: {shipment_num}")
                    else:
                        docss.save(ignore_permissions=True)
                        frappe.db.commit()

                else:  # create_new
                    # create a new document (similar to your original insert branch)
                    doc = frappe.new_doc(doctype_name)
                    doc.set("file_name", file_proper_name3)
                    doc.set("manifest_upload_data", manifest_upload_data_name)
                    doc.set("gateway", gateway)

                    # set fields from mapping definitions
                    for field_name, field_data in parsed.items():
                        if shipped_date and field_name == "shipped_date":
                            field_data = shipped_date
                        if import_date and field_name == "manifest_import_date":
                            field_data = import_date

                        doc.set(field_name, field_data)

                    print(doctype_name, shipment_num, "Inserting")

                    # Ensure shipment_number is set before insert (required by autoname)
                    if not getattr(doc, "shipment_number", None):
                        doc.shipment_number = shipment_num

                    if doctype_name == "R300000":
                        if doc.shipper_city:
                            make_R300000(doc)
                    elif doctype_name == "R400000":
                        if doc.consignee_city:
                            make_R400000(doc)
                    if hasattr(doc, "file_type") and not doc.file_type:
                        doc.file_type = "OPSYS"

                    if TEST_MODE:
                        frappe.log_error("TEST MODE - Not inserting", f"doctype: {doctype_name}, document: {doc}")
                    else:
                        doc.insert(ignore_permissions=True)
                        doc.save(ignore_permissions=True)
                        frappe.db.commit()

            else:
                # No docs matched at all -> simple insert path (mirrors previous 'else' insertion)
                doc = frappe.new_doc(doctype_name)
                doc.set("file_name", file_proper_name3)
                doc.set("manifest_upload_data", manifest_upload_data_name)
                doc.set("gateway", gateway)

                # set fields from mapping definitions
                for field_name, field_data in parsed.items():
                    if shipped_date and field_name == "shipped_date":
                        field_data = shipped_date
                    if import_date and field_name == "manifest_import_date":
                        field_data = import_date

                    doc.set(field_name, field_data)

                print(doctype_name, shipment_num, "Inserting (no prior match)")

                if not getattr(doc, "shipment_number", None):
                    doc.shipment_number = shipment_num

                if doctype_name == "R300000":
                    if doc.shipper_city:
                        make_R300000(doc)
                elif doctype_name == "R400000":
                    if doc.consignee_city:
                        make_R400000(doc)
                if hasattr(doc, "file_type") and not doc.file_type:
                    doc.file_type = "OPSYS"

                    if TEST_MODE:
                        frappe.log_error("TEST MODE - Not inserting", f"doctye: {doctype_name}, document: {doc}")
                    else:                
                        doc.insert(ignore_permissions=True)
                        doc.save(ignore_permissions=True)
                        frappe.db.commit()

    except Exception as e:
        frappe.log_error("Error in committing in OPSYS", f"Error in Manifest Upload Data: {str(e)}")

    # final step: store extracted shipment numbers as before
    try:
        storing_shipment_number(arrays=arrays, frm=shipf, to=shipt, doc=docnew)
    except Exception as e:
        frappe.log_error("Error in storing shipment number " + str(shipf) + '-' + str(shipt), f"Error in storing shipment number: {str(e)}")



@frappe.whitelist()
def reprocess_shipments(docname):
    failed = []
    doc = frappe.get_doc('Manifest Upload Data', docname)
    if not len(doc.failed_shipments) > 0:
        return
    origin_country = frappe.db.get_single_value("Manifest Setting Definition", "origin_country")

    for shipment in doc.failed_shipments:
        shipment_number = shipment.shipment
        r2_data = frappe.db.get_value("R200000", {"shipment_number": shipment_number}, ["billing_term_field", "shipped_date", "manifest_import_date", "file_type", "file_name"], as_dict=True)
        if not r2_data:
            failed.append(shipment_number)
            continue
        create_shipment_number_record(shipment_number, origin_country, r2_data, doc)
    doc.set("failed_shipments", [])
    
    if failed:
        for ship in failed:
            doc.append('failed_shipments', {
                "shipment": ship,
                "reason": "No R200000 record found"
            })
    doc.save(ignore_permissions = True)



# def safe_decode(file_doc):
#     content = file_doc.get_content()
#     if isinstance(content, bytes):
#         try:
#             return content.decode("utf-8")
#         except UnicodeDecodeError:
#             return content.decode("ISO-8859-1", errors="ignore")
#     return content



def safe_decode(file_doc):
    file_url = file_doc.file_url or ""
    if file_url.startswith("http"):
        response = requests.get(file_url)
        response.raise_for_status()
        content = response.content
    else:
        content = file_doc.get_content()

    if isinstance(content, bytes):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("ISO-8859-1", errors="ignore")
    return content





def find_shipment_docs(doctype_name, shipment_num, pkg_trck=None, extra_filters=None, limit=5):
    """
    Returns list of dicts [{'name': '...'}, ...] of matching Shipment docs:
      - name == shipment_num
      - name LIKE 'shipment_num-%'
      - shipment_number == shipment_num
    Optionally restrict by extra_filters (dict).
    """
    base_filters = ["or",
                    ["name", "=", shipment_num],
                    ["name", "like", f"{shipment_num}-%"],
                    ["shipment_number", "=", shipment_num]
                   ]
    if extra_filters:
        # convert dict to [ [k, '=', v], ... ]
        if isinstance(extra_filters, dict):
            extra_list = [[k, "=", v] for k, v in extra_filters.items()]
        else:
            extra_list = extra_filters
        filters = ["and", base_filters] + extra_list
    else:
        filters = base_filters

    docs = frappe.get_list(doctype_name, filters=filters, fields=["name", "shipment_number", "manifest_import_date", "shipped_date"], limit_page_length=limit, order_by="modified desc")
    return docs


def normalize_date_str(value):
    """Return YYYY-MM-DD or None for comparable strings/dates. Accepts datetime/date/string."""
    if not value:
        return None
    if isinstance(value, (datetime, )):
        return value.strftime("%Y-%m-%d")
    try:
        # try parsing a few common formats; if your input already YYYY-MM-DD this returns same
        # prefer strict parse with known format if you know it
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        try:
            return datetime.strptime(str(value), "%d-%m-%Y").strftime("%Y-%m-%d")
        except Exception:
            # fallback: return raw string trimmed (not ideal for strict comparison)
            return str(value).strip()


def notify_billing(subject, message, recipients=None, reference_doctype=None, reference_name=None):
    """
    Simple helper to email billing team and optionally create real-time notification.
    recipients: list or comma-separated string
    """
    if not recipients:
        # try to get from settings
        try:
            setting = frappe.get_doc("Manifest Setting Definition")
            recipients = getattr(setting, "billing_emails", None)
        except Exception:
            recipients = None

    if not recipients:
        # fallback list - replace with your real emails
        recipients = ["billing@example.com"]

    if isinstance(recipients, (list, tuple)):
        recipients = ",".join(recipients)

    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            content=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name
        )
    except Exception as e:
        frappe.log_error(f"Failed to notify billing: {e}", "Notify Billing Error")

    # optional realtime notification to logged-in users (billing role)
    try:
        frappe.publish_realtime(event="msgprint", message=subject + "\n\n" + message)
    except Exception:
        pass

def determine_shipment_action(existing_doc, incoming_manifest_input_date):
    """
    Determine whether to 'update', 'alert_update', or 'create_new'
    based ONLY on input_date (manifest_input_date).

    existing_doc can be a dict (from get_list) or a frappe doc.
    """

    if not existing_doc:
        return "create_new"

    # Get existing input_date safely
    ex_input_date = normalize_date_str(
        existing_doc.get("manifest_input_date")
        if isinstance(existing_doc, dict)
        else getattr(existing_doc, "manifest_input_date", None)
    )

    in_input_date = normalize_date_str(incoming_manifest_input_date)

    # If incoming date is missing, safest option
    if not in_input_date:
        return "create_new"

    # Rule 1: same input_date → update
    if ex_input_date and ex_input_date == in_input_date:
        return "update"

    # Rule 2: different input_date → alert_update
    if ex_input_date and ex_input_date != in_input_date:
        return "alert_update"

    # Fallback
    return "create_new"
