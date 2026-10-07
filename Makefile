.PHONY: test bench demo clean

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

bench:
	$(PYTHON) benchmarks/bench_solvers.py

demo:
	$(PYTHON) examples/quickstart.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info
