.PHONY: test bench bench-eval eval demo demo-eval clean

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

bench:
	$(PYTHON) benchmarks/bench_solvers.py

bench-eval:
	$(PYTHON) benchmarks/run_swe_and_e2e_eval.py

eval:
	$(PYTHON) -m unittest tests/test_swe_and_e2e.py -v

demo:
	$(PYTHON) examples/quickstart.py

demo-eval:
	$(PYTHON) examples/swe_and_e2e_demo.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info
