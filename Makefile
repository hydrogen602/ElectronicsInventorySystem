compose-command := docker-compose

# allow CORS access for frontend (e.g. create-react-app)
run: export ALLOWED_FRONTEND_URLS = http://localhost:3000
run: export ENV = dev

run:
	poetry run fastapi dev electronic_inv_sys

run-ui:
	$(MAKE) -C ui run-local

prepare-build:
	$(MAKE) -C ui prepare-build

coverage-cli:
	poetry run pytest --cov

coverage-html:
	poetry run pytest --cov --cov-report=html:coverage_report

coverage: coverage-html
	open 'http://localhost:3000'
	# requires npm tool serve
	serve --no-port-switching coverage_report/

oauth:
	poetry run python oauth.py

# -----

# use docker-compose.yml

# build and deploy the rust container
run-docker: prepare-build stop-docker
	$(compose-command) -f docker-compose.yml up -d --build

# helper
stop-docker:
	$(compose-command) -f docker-compose.yml down 