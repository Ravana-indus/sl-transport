__version__ = '0.0.1'

app_name = "public_transport"
app_title = "Public Transport"
app_publisher = "Your Name"
app_description = "Public Transport Management System"
app_email = "your.email@example.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/public_transport/css/public_transport.css"
# app_include_js = "/assets/public_transport/js/public_transport.js"

# include js, css files in header of web template
# web_include_css = "/assets/public_transport/css/public_transport.css"
# web_include_js = "/assets/public_transport/js/public_transport.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "public_transport/public/scss/website"

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

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "public_transport.install.before_install"
# after_install = "public_transport.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "public_transport.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# "*": {
# frappe-env/"on_update": "method",
# frappe-env/"on_cancel": "method",
# frappe-env/"on_trash": "method"
#}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# "all": [
# frappe-env/"public_transport.tasks.all"
# ],
# "daily": [
# frappe-env/"public_transport.tasks.daily"
# ],
# "hourly": [
# frappe-env/"public_transport.tasks.hourly"
# ],
# "weekly": [
# frappe-env/"public_transport.tasks.weekly"
# ]
# "monthly": [
# frappe-env/"public_transport.tasks.monthly"
# ]
# }

# Testing
# -------

# before_tests = "public_transport.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# "frappe.desk.doctype.event.event.get_events": "public_transport.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# "Task": "public_transport.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]
