.PHONY: test demo lint docker-build clean

test:
	PYTHONPATH=core:components/01-semantic-telemetry-otel:components/02-k8s-semantic-action-gate:components/03-sre-agent-dual-loop:components/04-progressive-delivery:components/05-incident-decomposition:components/06-ci-semantic-pathfinder python3 -m unittest discover -s tests -p "test_*.py" -v

demo:
	bash demos/run_all_demos.sh

lint:
	helm lint helm/jevops-suite

docker-build:
	docker build -t ghcr.io/nubenetes/jevops-decision-engine:v0.1.0 -f airgap-decision-server/Dockerfile .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
