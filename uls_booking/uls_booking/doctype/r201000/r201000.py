# Copyright (c) 2024, fariz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class R201000(Document):

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
            self.invoice_custom_complement_for_revenue_chargestotal = safe_divide_100(self.custom_complement_for_revenue_charges)
            self.custom_minimum_bill_weight = safe_divide_10(self.custom_minimum_bill_weight)

            self.custom_201surchargeamt1 = safe_divide_100(self.custom_201surchargeamt1)
            self.custom_201surchargeamt2 = safe_divide_100(self.custom_201surchargeamt2)
            self.custom_201surchargeamt3 = safe_divide_100(self.custom_201surchargeamt3)
            self.custom_201surchargeamt4 = safe_divide_100(self.custom_201surchargeamt4)
            self.custom_201surchargeamt5 = safe_divide_100(self.custom_201surchargeamt5)
            self.custom_201surchargeamt6 = safe_divide_100(self.custom_201surchargeamt6)
            self.custom_201surchargeamt7 = safe_divide_100(self.custom_201surchargeamt7)
            self.custom_201surchargeamt8 = safe_divide_100(self.custom_201surchargeamt8)
            self.custom_201surchargeamt9 = safe_divide_100(self.custom_201surchargeamt8)
            self.custom_201surchargeamt10 = safe_divide_100(self.custom_201surchargeamt10)
            self.custom_201surchargeamt11 = safe_divide_100(self.custom_201surchargeamt11)
            self.custom_201surchargeamt12 = safe_divide_100(self.custom_201surchargeamt12)
            self.custom_201surchargeamt13 = safe_divide_100(self.custom_201surchargeamt13)
            self.custom_201surchargeamt14 = safe_divide_100(self.custom_201surchargeamt14)
            self.custom_201surchargeamt15 = safe_divide_100(self.custom_201surchargeamt15)
            self.custom_ws201surchargeamt16 = safe_divide_100(self.custom_ws201surchargeamt16)
            self.custom_ws201surchargeamt17 = safe_divide_100(self.custom_ws201surchargeamt17)
            self.custom_ws201surchargeamt18 = safe_divide_100(self.custom_ws201surchargeamt18)
            self.custom_ws201surchargeamt19 = safe_divide_100(self.custom_ws201surchargeamt19)
            self.custom_ws201surchargeamt20 = safe_divide_100(self.custom_ws201surchargeamt20)
            
            self.check = 1


    # pass
                   