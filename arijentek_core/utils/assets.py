import json
import os

import frappe


def get_frontend_asset(app_name, entry_point):
	"""
	Returns the resolved asset path from manifest.json for a given frontend app.
	app_name: 'pos' or 'employee-portal'
	entry_point: the source filename (e.g., 'index.js' or 'index.css')
	"""
	app_path = frappe.get_app_path("arijentek_core")
	base_url_prefix = "arijentek_core"

	# Paths for manifest
	# Note: Vite 5+ puts it in .vite/manifest.json, older versions in manifest.json
	manifest_paths = [
		os.path.join(app_path, "public", app_name, ".vite", "manifest.json"),
		os.path.join(app_path, "public", app_name, "manifest.json"),
	]

	manifest = {}
	for path in manifest_paths:
		if os.path.exists(path):
			with open(path) as f:  # nosemgrep: frappe-security-file-traversal
				manifest = json.load(f)
			break

	if not manifest:
		return ""

	# Vite manifests usually map 'src/main.js' or similar to the built file
	# We might need to handle different entry point names depending on the app's vite config

	# Try direct entry point match
	asset_info = manifest.get(entry_point)

	# If not found, try common entry point paths used by frappe-ui/vite
	if not asset_info:
		for key in manifest.keys():
			if key.endswith(entry_point):
				asset_info = manifest[key]
				break

	# Vite building with index.html as entry point
	if not asset_info and "index.html" in manifest:
		entry = manifest["index.html"]
		if entry_point.endswith(".js"):
			return f"/assets/{base_url_prefix}/{app_name}/{entry['file']}"
		elif entry_point.endswith(".css") and "css" in entry and list(entry["css"]):
			return f"/assets/{base_url_prefix}/{app_name}/{entry['css'][0]}"

	if asset_info:
		file_name = asset_info.get("file")
		if file_name:
			return f"/assets/{base_url_prefix}/{app_name}/{file_name}"

	return ""
