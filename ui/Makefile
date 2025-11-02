SHELL := /bin/bash
APP_NAME := electronic-inv-sys-ui



run-local: export REACT_APP_INV_API=http://127.0.0.1:8000

run: gen-openapi
	npm run start

run-local: gen-openapi
	npm run start

ALL_PY_FILES := $(shell find ../electronic_inv_sys -name '*.py')

openapi/inventory.json: $(ALL_PY_FILES) 
	cd .. && poetry run python openapi.py ui/$@

gen-openapi: src/openapi/marker
src/openapi/marker: openapi/inventory.json
	openapi-generator generate -i $< -g typescript-fetch -o src/openapi/inventory 
	touch $@
#--additional-properties modelPropertyNaming=original

prepare-build: gen-openapi
