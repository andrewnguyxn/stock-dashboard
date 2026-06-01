.PHONY: install run pipeline test

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

pipeline:
	python pipeline.py

test:
	pytest -q
