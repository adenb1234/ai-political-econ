# Prefer project venv when present (pyarrow/pandas for LocalView geo).
PYTHON ?= $(shell if [ -x "$(CURDIR)/.venv/bin/python" ]; then echo "$(CURDIR)/.venv/bin/python"; else echo python3; fi)
export PYTHONPATH := $(CURDIR)

.PHONY: help fetch-census fetch-census-places fetch-ccc fetch-eia fetch-lbnl fetch-localview fetch-localview-meta fetch-docs fetch-all fips-summary crosswalk-localview spine-localview manifests transform-ccc

help:
	@echo "Targets:"
	@echo "  make fetch-census          Download Census county FIPS gazetteer"
	@echo "  make fetch-census-places   Download Census places gaz + national_places"
	@echo "  make fetch-ccc             Download CCC phase-3 public CSV"
	@echo "  make fetch-eia             Download EIA-861 2024 zip"
	@echo "  make fetch-lbnl            Download LBNL Queued Up 2026 XLSX"
	@echo "  make fetch-localview       Download LocalView codebook"
	@echo "  make fetch-localview-meta  Codebook + meta + county/month spine v0"
	@echo "  make fetch-docs            Write manifests for key-gated / huge sources"
	@echo "  make fetch-all             All of the above"
	@echo "  make transform-ccc         CCC CSV → AI-related events + mobilization panel"
	@echo "  make crosswalk-localview   LocalView meta → county FIPS crosswalk v0"
	@echo "  make spine-localview       LocalView meta + crosswalk → county_fips + month spine v0"
	@echo "  make fips-summary          Summarize local FIPS table"
	@echo "  make manifests             Refresh documentation manifests only"

fetch-census:
	$(PYTHON) -m src.ingest.census_fips

fetch-census-places:
	$(PYTHON) -m src.ingest.census_places

fetch-ccc:
	$(PYTHON) -m src.ingest.ccc

fetch-eia:
	$(PYTHON) -m src.ingest.eia_861

fetch-lbnl:
	$(PYTHON) -m src.ingest.lbnl_queued_up

fetch-localview:
	$(PYTHON) -m src.ingest.localview

fetch-localview-meta:
	$(PYTHON) -m src.ingest.localview --include-meta

fetch-docs:
	$(PYTHON) -m src.ingest.legiscan
	$(PYTHON) -m src.ingest.openstates
	$(PYTHON) -m src.ingest.arctic_shift
	$(PYTHON) -m src.ingest.media_cloud
	$(PYTHON) -m src.ingest.project_ledger

fetch-all: fetch-census fetch-census-places fetch-ccc fetch-eia fetch-lbnl fetch-localview fetch-docs

transform-ccc:
	$(PYTHON) -m src.transform.ccc_to_events

crosswalk-localview: fetch-census fetch-census-places
	$(PYTHON) -m src.transform.localview_geo

spine-localview:
	$(PYTHON) -m src.transform.localview_meta_spine

fips-summary:
	$(PYTHON) -m src.geo.fips --summary

manifests: fetch-docs
