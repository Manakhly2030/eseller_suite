# Copyright (c) 2024, efeone and contributors
# For license information, please see license.txt


from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, today, getdate


class AmazonSPAPISettings(Document):
	def validate(self):
		self.validate_after_date()

		if self.is_active == 0:
			self.enable_sync = 0

		if not self.max_retry_limit:
			self.max_retry_limit = 1
		elif self.max_retry_limit and self.max_retry_limit > 5:
			frappe.throw(frappe._("Value for <b>Max Retry Limit</b> must be less than or equal to 5."))

	def save(self):
		super(AmazonSPAPISettings, self).save()

		# if not self.is_old_data_migrated:
		# 	self.db_set("is_old_data_migrated", 1)

	def validate_after_date(self):
		if datetime.strptime(add_days(today(), -30), "%Y-%m-%d") > datetime.strptime(
			self.after_date, "%Y-%m-%d"
		):
			frappe.throw(_("The date must be within the last 30 days."))

	@frappe.whitelist()
	def get_order_details(self):
		from eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository import (
			get_orders,
		)
		if self.is_active == 1:
			job_name = f"Get Amazon Orders - {self.name}"

			if frappe.db.get_all("RQ Job", {"job_name": job_name, "status": ["in", ["queued", "started"]]}):
				return frappe.msgprint(_("The order details are currently being fetched in the background."))

			frappe.enqueue(
				job_name=job_name,
				method=get_orders,
				amz_setting_name=self.name,
				last_updated_after=self.after_date,
				sync_selected_date_only=self.sync_selected_date_only,
				timeout=6000,
				now=frappe.flags.in_test,
			)

			frappe.msgprint(_("Order details will be fetched in the background."))
		else:
			frappe.msgprint(
				_("Please enable the Amazon SP API Settings {0}.").format(frappe.bold(self.name))
			)
 

# Called via a hook in every hour.
def schedule_get_order_details():
	from eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository import (
		get_orders,
	)
	current_date = getdate().strftime( "%Y-%m-%d")
	# next_date = add_days(getdate(), 1).strftime( "%Y-%m-%d")

	amz_settings = frappe.get_all(
		"Amazon SP API Settings",
		filters={"is_active": 1, "enable_sync": 1},
		fields=["name"],
	)

	for amz_setting in amz_settings:
		get_orders(amz_setting_name=amz_setting.name, last_updated_after=current_date)
