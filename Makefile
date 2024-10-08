.PHONY: run
run: .venv
	.venv/bin/python computer.py

.PHONY: test-vosk
test-vosk: .venv
	.venv/bin/python vosk_listener.py

.venv: requirements.txt
	python -m venv .venv --clear
	.venv/bin/pip install -r requirements.txt
	touch .venv

requirements.txt: requirements.in
	python -m venv tmpvenv --clear
	tmpvenv/bin/pip install -r requirements.in
	tmpvenv/bin/pip freeze > requirements.txt
	rm -rf tmpvenv

.PHONY: run-whisper
run-whisper: .venv
	.venv/bin/pip install openai-whisper
	.venv/bin/python computer.py --whisper

.PHONY: test-whisper
test-whisper: .venv
	.venv/bin/pip install openai-whisper
	.venv/bin/python whisper_listener.py

.PHONY: clean
clean:
	rm -rf .venv
