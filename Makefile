PYTHON ?= python3
export PYTHONPATH := $(CURDIR)

.PHONY: help fetch-census fetch-ccc fetch-eia fetch-localview fetch-docs fetch-all fips-summary manifests

help:
	@echo "Targets:"
	@echo "  make fetch-census     Download Census county FIPS gazetteer"
	@echo "  make fetch-ccc        Download CCC phase-3 public CSV"
	@echo "  make fetch-eia        Download EIA-861 2024 zip"
	@echo "  make fetch-localview  Download LocalView codebook"
	@echo "  make fetch-docs       Write manifests for key-gated / huge sources"
	@echo "  make fetch-all        All of the above"
	@echo "  make fips-summary     Summarize local FIPS table"
	@echo "  make manifests        Refresh documentation manifests only"

fetch-census:
	$(PYTHON) -m src.ingest.census_fips

fetch-ccc:
	$(PYTHON) -m src.ingest.ccc

fetch-eia:
	$(PYTHON) -m src.ingest.eia_861

fetch-localview:
	$(PYTHON) -m src.ingest.localview

fetch-docs:
	$(PYTHON) -m src.ingest.legiscan
	$(PYTHON) -m src.ingest.openstates
	$(PYTHON) -m src.ingest.arctic_shift
	$(PYTHON) -m src.ingest.media_cloud
	$(PYTHON) -m src.ingest.project_ledger

fetch-all: fetch-census fetch-ccc fetch-eia fetch-localview fetch-docs

fips-summary:
	$(PYTHON) -m src.geo.fips --summary

manifests: fetch-docs
