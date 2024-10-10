# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import requests


class ICRISAccount(Document):
	# pass
	def before_save(self) :
		url = "https://wwwcie.ups.com/security/v1/oauth/authorize"

		query = {
			'client_id' : 'gA6mdvAvD2A7RgNLAWvxCviPX31GPSlh2FJ31dUEToDBXniS' ,
			'redirect_uri' : 'https://onlinetools.ups.com' ,
			'response_type' : 'code' ,
		}

		response = requests.get(url, params=query)

		data = response.json()
		frappe.msgprint(str(data))




