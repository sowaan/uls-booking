app_name = "uls_booking"
app_title = "ULS Booking"
app_publisher = "Sowaan"
app_description = "Booking app for ULS."
app_email = "sufyan.sadiq@sowaan.com"
app_license = "mit"
# required_apps = []




fixtures = [
    {
      "doctype" : "Custom Field",
      "filters" : [
        [  
          "fieldname" , "in" , (

                                "custom_booking",
                                "custom_icris_account",

                                "custom_import_control",
                                "custom_exempt_codes",
                                "custom_extended_area_surcharge",
                                "custom_additional_handling_charges",
                                "custom_shipping_bill_charges_applicable",
                                "custom_allow_saturday_delivery",
                                "custom_return_electronic_label",
                                "custom_residential_surcharge",
                                "custom_remote_area_surcharge",
                                "custom_large_package_surcharge",
                                "custom_allow_direct_delivery_only",
                                "custom_dutytax_forwarding_surcharge",
                                "custom_insurance_of_declared_value",
                                "custom_over_maximum_limit",
                                "custom_applicable_surcharges_and_amount",

                                
                                

                                "custom_service_types",
                                "custom_consignee_number",
                                "custom_shipper_number",
                                "custom_tracking_number",
                                "custom_shipper_postal_code",
                                "custom_shipper_phone_number",
                                "custom_shipper_name",
                                "custom_shipper_country",
                                "custom_shipper_contact_name",
                                "custom_shipper_city",
                                "custom_shipment_weight_unit",
                                "custom_shipment_weight",
                                "custom_shipment_type",
                                "custom_shipment_number",
                                "custom_service_type",
                                "custom_selling_percentage",
                                "custom_packages",
                                "custom_manifest",
                                "custom_insurance_charges",
                                "custom_insurance_amount",
                                "custom_date_shipped",
                                "custom_consignee_postal_code",
                                "custom_consignee_phone_number",
                                "custom_consignee_name",
                                "custom_consignee_country",
                                "custom_consignee_contact_name",
                                "custom_consignee_city",
                                "custom_booking_date",
                                "custom_billing_term",
                                "custom_default_customer",
                                "custom_duty_and_taxes_sales_invoice_uploader",
                                "custom_duty_and_taxes_template",
                                "custom_duty_and_taxes_invoice",
                                "custom_consignee_building",
                                "custom_consignee_street",
                                "custom_mawb_number",
                                "custom_type",
                                "custom_location",
                                "custom_clearance_type",
                                "custom_zone",
                                "custom_strn",
                                "custom_hs_code",
                                
                                "custom_package_type",
                                "custom_billing_type",
                                "custom_province",
                                "custom_surchages_code_and_amount",
                                "custom_surcharge_excl_fuel",
                                "custom_total_surcharges_excl_fuel",
                                "custom_column_break_en4jc",
                                "custom_surcharge_incl_fuel",
                                "custom_total_surcharges_incl_fuel",
                                "custom_column_break_uzjnx",
                                "custom_column_break_kwj1v",
                                "custom_column_break_vg9j9",
                                "custom_arrival_date",
                                "custom_expanded_invoice_total",
                                "custom_currency_code_for_invoice_total",
                                "custom_compensation_invoices",
                                "custom_freight_invoices",
                                "custom_amount_after_discount",

                                "custom_duty_and_taxes",
                                "custom_mawb_number",
                                "custom_flight_number",
                                "custom_column_break_dpuye",
                                "custom_arrival_date",
                                "custom_mno",
                                "custom_duty_and_taxes_invoice",
                                "custom_dt_vendor",
                                "custom_shipping_billing_charges",
                                "custom_exempt_gst",
                                "custom_sales_invoice_definition",
                                "custom_invoice_logs",
                                "custom_sales_invoice_log",



                                "custom_freight_charges",
                                "custom_inserted"

                                )
	  	  
        ]  
      ]
	}
#   ,
#     {
#         "doctype" : "Client Script",
#       "filters" : [
#         [  
#           "name" , "=" , "Selling Percentage"
# ]
#       ]



#     }



]

# include js in doctype views
doctype_js = {
    "Sales Invoice" : "uls_booking/client_scripts/sales_invoice.js",
    "HD Ticket" : "uls_booking/client_scripts/hd_ticket.js"
}








# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/uls_booking/css/uls_booking.css"
# app_include_js = "/assets/uls_booking/js/uls_booking.js"

# include js, css files in header of web template
# web_include_css = "/assets/uls_booking/css/uls_booking.css"
# web_include_js = "/assets/uls_booking/js/uls_booking.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "uls_booking/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "uls_booking/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "uls_booking.utils.jinja_methods",
# 	"filters": "uls_booking.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "uls_booking.install.before_install"
# after_install = "uls_booking.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "uls_booking.uninstall.before_uninstall"
# after_uninstall = "uls_booking.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "uls_booking.utils.before_app_install"
# after_app_install = "uls_booking.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "uls_booking.utils.before_app_uninstall"
# after_app_uninstall = "uls_booking.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "uls_booking.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {

# }



# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Customer": {
		"before_save": "uls_booking.uls_booking.api.api.check_user_permission",
	},
  "Sales Invoice": {
    "before_save": "uls_booking.uls_booking.events.sales_invoice.generate_invoice",
    # "before_save": "uls_booking.uls_booking.events.sales_invoice.restore_values",
    "before_submit": "uls_booking.uls_booking.events.sales_invoice.duty_and_tax_validation_on_submit",
  },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
#	 "all": [
#		 "uls_booking.tasks.daily"
#	 ],
# 	"daily": [
# 		"uls_booking.tasks.daily"
# 	],
	"hourly": [
		"uls_booking.uls_booking.api.api.tracking_shipments",
    
	],
    
    "cron": {
        "*/25 * * * * *": [
        	"uls_booking.uls_booking.doctype.manifest_upload_data.manifest_upload_data.generate_remaining_sales_invoice"
		],
	},
# 	"weekly": [
# 		"uls_booking.tasks.weekly"
# 	],
# 	"monthly": [
# 		"uls_booking.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "uls_booking.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "uls_booking.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "uls_booking.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["uls_booking.utils.before_request"]
# after_request = ["uls_booking.utils.after_request"]

# Job Events
# ----------
# before_job = ["uls_booking.utils.before_job"]
# after_job = ["uls_booking.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"uls_booking.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

