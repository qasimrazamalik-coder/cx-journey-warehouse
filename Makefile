# Convenience targets (on Windows without make, run the python commands directly).
.PHONY: build fast client-b test docs clean

build:      ## full-scale build, client A dialer
	python scripts/build.py

fast:       ## 15% scale, about a minute
	python scripts/build.py --scale 0.15

client-b:   ## onboard client B's dialer export: same models, one var
	python scripts/build.py --scale 0.15 --dialer-format events

test:
	pytest -q

docs:
	cd dbt && CX_WAREHOUSE_PATH=../warehouse.duckdb dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

clean:
	rm -rf warehouse.duckdb dbt/target dbt/logs
