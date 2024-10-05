.PHONY: run
run: .venv
	.venv/bin/python computer.py

.venv: requirements.txt
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt
	touch .venv

requirements.txt: requirements.in
	python -m venv tmpvenv
	tmpvenv/bin/pip install -r requirements.in
	tmpvenv/bin/pip freeze > requirements.txt
	rm -rf tmpvenv
