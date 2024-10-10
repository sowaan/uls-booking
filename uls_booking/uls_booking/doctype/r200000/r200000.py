# Copyright (c) 2024, fariz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from datetime import datetime




class R200000(Document):

    def before_save(self):
        # Define helper functions for division outside of the if block
        def safe_divide_10(value):
            try:
                return float(value) / 10
            except (ValueError, TypeError):
                return 0.0  # Return a default value in case of error

        def safe_divide_100(value):
            try:
                return float(value) / 100
            except (ValueError, TypeError):
                return 0.0  # Return a default value in case of error

        # Check the condition and process accordingly
        if self.check == 0:
            date_format = "%d%b%Y"
            date_input = self.input_date
            date_object_input = datetime.strptime(date_input, date_format)
            formatted_input_date = date_object_input.strftime("%Y-%m-%d")
            self.input_date = formatted_input_date

            # Convert date_shipped
            date_shipped = self.date_shipped
            date_object_shipped = datetime.strptime(date_shipped, date_format)
            formatted_date_shipped = date_object_shipped.strftime("%Y-%m-%d")
            self.date_shipped = formatted_date_shipped

            # Apply the helper functions to each relevant attribute
            self.invoice_total = safe_divide_100(self.invoice_total)
            self.expanded_invoice_total = safe_divide_100(self.expanded_invoice_total)
            self.custom_weight_of_1st_package_in_shipment = safe_divide_10(self.custom_weight_of_1st_package_in_shipment)
            self.custom_1st_package_revenue = safe_divide_100(self.custom_1st_package_revenue)
            self.shipment_weight = safe_divide_10(self.shipment_weight)
            self.freight_charges = safe_divide_100(self.freight_charges)
            self.dimensional_weight = safe_divide_10(self.dimensional_weight)
            self.declared_value = safe_divide_100(self.declared_value)

            # Update the check attribute
            self.check = 1






        # setting = frappe.get_doc("Manifest Setting Definition")

        # # for i in setting.manifest_setting:
        # #     if i.record == self.name:
        # #         field_value = getattr(self, i.field_name, None)
        # #         if field_value == i.code:
        # #             setattr(self, i.field_name, i.replacement)




        # country_map = {j.code: j.country for j in setting.country_codes}

        # doctype = self.doctype

        # # Iterate over field names and records
        # for field_info in setting.field_names_and_records:
        #     if field_info.record == doctype:
        #         field_value = getattr(self, field_info.field_name, None)
        #         # Only set the attribute if the field value exists in the country map
        #         if field_value in country_map:
        #             # Directly set the country name if found
        #             setattr(self, field_info.field_name, country_map[field_value])




        
                    
                    
        # file_destin = frappe.get_doc("File destin")
        # file_name = frappe.db.get_value("File", {"file_url": file_destin.file}, "name")
        # file_doc = frappe.get_doc("File", file_name)
        # content = file_doc.get_content()
        # arrays = content.split('\n')



        # file_destin = frappe.get_doc("File destin")
        # file_name1 = frappe.db.get_value("File", {"file_url": file_destin.country}, "name")
        # file_doc1 = frappe.get_doc("File", file_name1)
        # content1 = file_doc1.get_content()
        # arrays1 = content1.split('\n')
        
        # for i in setting.manifest_setting:
        #     # Check if the field `i.record` is None or an empty string
        #     if not i.record:  # This checks for both None and empty string
        #         i.record = "R200000"  # Set the value to "R200000"





        # if len(arrays) != len(arrays1):
        #     frappe.throw("The length of country codes and country names do not match.")

        # # Append rows to the manifest_setting child table
        # for i in range(len(arrays)):
        #     row = {"code": arrays[i], "replacement": arrays1[i]}
        #     setting.append("manifest_setting", row)
        # setting.save()