# Copyright (c) 2024, fariz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
class R202000(Document):

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
            # Apply the helper functions to each relevant attribute
            
            self.custom_expanded_1st_package_weight = safe_divide_10(self.custom_expanded_1st_package_weight)
            self.shipper_freight_amount = safe_divide_100(self.shipper_freight_amount)
            self.custom_pickup_compensation_amount = safe_divide_100(self.custom_pickup_compensation_amount)
            self.custom_delivery_compensation_amount = safe_divide_100(self.custom_delivery_compensation_amount)
            self.custom_expanded_shipment_weight = safe_divide_10(self.custom_expanded_shipment_weight)
           
            
            # Update the check attribute
            self.check = 1
    # pass