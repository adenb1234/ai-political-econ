# Prefer project venv when present (pyarrow/pandas for LocalView geo).
PYTHON ?= $(shell if [ -x "$(CURDIR)/.venv/bin/python" ]; then echo "$(CURDIR)/.venv/bin/python"; else echo python3; fi)
export PYTHONPATH := $(CURDIR)

.PHONY: help fetch-census fetch-census-places fetch-ccc fetch-eia fetch-lbnl fetch-moratorium-nation fetch-ai-gridwatch fetch-localview fetch-localview-meta fetch-docs fetch-all fips-summary crosswalk-localview spine-localview manifests transform-ccc transform-c-moratoria

help:
	@echo "Targets:"
	@echo "  make fetch-census          Download Census county FIPS gazetteer"
	@echo "  make fetch-census-places   Download Census places gaz + national_places + place_by_county_2020 + CT town→COG"
	@echo "  make fetch-ccc             Download CCC phase-3 public CSV"
	@echo "  make fetch-eia             Download EIA-861 2024 zip"
	@echo "  make fetch-lbnl            Download LBNL Queued Up 2026 XLSX"
	@echo "  make fetch-moratorium-nation  Download Moratorium Nation CSVs (layer C)"
	@echo "  make fetch-ai-gridwatch    Download AI GridWatch open-data CSVs (layer C/G)"
	@echo "  make fetch-localview       Download LocalView codebook"
	@echo "  make fetch-localview-meta  Codebook + meta + county/month spine v0"
	@echo "  make fetch-docs            Write manifests for key-gated / huge sources"
	@echo "  make fetch-all             All of the above"
	@echo "  make transform-ccc         CCC CSV → AI-related events + mobilization panel"
	@echo "  make transform-c-moratoria Moratorium Nation + AI GridWatch place→county stubs"
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

fetch-moratorium-nation:
	$(PYTHON) -m src.ingest.moratorium_nation

fetch-ai-gridwatch:
	$(PYTHON) -m src.ingest.ai_gridwatch

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

fetch-all: fetch-census fetch-census-places fetch-ccc fetch-eia fetch-lbnl fetch-moratorium-nation fetch-ai-gridwatch fetch-localview fetch-docs

transform-ccc:
	$(PYTHON) -m src.transform.ccc_to_events

transform-c-moratoria:
	$(PYTHON) -m src.transform.c_moratoria_geo_stub

crosswalk-localview: fetch-census fetch-census-places
	$(PYTHON) -m src.transform.localview_geo

spine-localview:
	$(PYTHON) -m src.transform.localview_meta_spine

fips-summary:
	$(PYTHON) -m src.geo.fips --summary

manifests: fetch-docs
