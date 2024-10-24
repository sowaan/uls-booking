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

            # # Apply the helper functions to each relevant attribute
            # self.invoice_total = safe_divide_100(self.invoice_total)
            # self.expanded_invoice_total = safe_divide_100(self.expanded_invoice_total)
            # self.custom_weight_of_1st_package_in_shipment = safe_divide_10(self.custom_weight_of_1st_package_in_shipment)
            # self.custom_1st_package_revenue = safe_divide_100(self.custom_1st_package_revenue)
            # self.shipment_weight = safe_divide_10(self.shipment_weight)
            # self.freight_charges = safe_divide_100(self.freight_charges)
            # self.dimensional_weight = safe_divide_10(self.dimensional_weight)
            # self.declared_value = safe_divide_100(self.declared_value)

            # # Update the check attribute
            # self.check = 1
