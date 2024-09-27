# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

# from frappe.model.naming import make_autoname
# import frappe

class BuyingRate(Document):
    def before_insert(self):
        if self.based_on == 'Zone':
            self.naming_series = self.rate_group + "-" + self.zone + "-" + self.package_type + "-"
            # self.naming_series = make_autoname(prefix + ".#####")
            # frappe.msgprint(self.naming_series)

        elif self.based_on == 'Country':
            self.naming_series = self.rate_group + "-" + self.country + "-" + self.package_type + "-"
            # self.naming_series = make_autoname(prefix + ".#####")
            # frappe.msgprint(self.naming_series)
