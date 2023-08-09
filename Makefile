format:
	isort . --profile 'black'
	black .

lint:
	mypy --disallow-untyped-defs --ignore-missing-imports .
	black . --check
	isort . --profile 'black' --check
	flake8 .

