# Makefile for InstalledCapacityReport


# ------------------------------------------------------------------------------
# Release information: Update for each release
# ------------------------------------------------------------------------------

PACKAGE := InstalledCapacityReport
VERSION := 1.0


# ------------------------------------------------------------------------------
# Internal variables: Do not change for a release
# ------------------------------------------------------------------------------

DIST_DIR:= dist_dir
TARBALL_DIR := $(PACKAGE)-$(VERSION)
TARBALL_NAME := $(PACKAGE)-$(VERSION).tar.gz
UPSTREAM := /p/vdt/public/html/upstream
UPSTREAM_DIR := $(UPSTREAM)/$(PACKAGE)/$(VERSION)


# ------------------------------------------------------------------------------

.PHONY: _default clean dist upstream

_default:
	@echo "There is no default target; choose one of the following:"
	@echo "  make dist                     --" \
	      "make a distribution source tarball"
	@echo "  make upstream [UPSTREAM=path] --" \
	      "install source tarball to upstream cache"

clean:
	rm -rf $(DIST_DIR) $(PACKAGE)-*.tar.gz

$(TARBALL_NAME):
	@# Ignore unversioned '?' files, complain about any other changes
	@if svn_status=$$(svn status 2>&1 | grep '^[^?]'); then \
	  echo "Uncommitted changes detected; please svn commit them first:"; \
	  echo "$$svn_status"; \
	else \
	  rm -rf $(DIST_DIR); \
	  mkdir $(DIST_DIR); \
	  svn export . $(DIST_DIR)/$(TARBALL_DIR); \
	  rm $(DIST_DIR)/$(TARBALL_DIR)/Makefile; \
	  tar czfC $(TARBALL_NAME) $(DIST_DIR) $(TARBALL_DIR); \
	  rm -rf $(DIST_DIR); \
	fi

dist: $(TARBALL_NAME)

upstream: $(TARBALL_NAME)
	@if ! test -d $(UPSTREAM); then \
	  echo "Must have existing upstream cache directory at '$(UPSTREAM)'"; \
	elif test -f $(UPSTREAM_DIR)/$(TARBALL_NAME); then \
	  echo "Source tarball already installed at" \
	       "'$(UPSTREAM_DIR)/$(TARBALL_NAME)'"; \
	  echo "Remove installed source tarball or increment release version"; \
	else \
	  mkdir -p $(UPSTREAM_DIR); \
	  install -p -m 0644 $(TARBALL_NAME) $(UPSTREAM_DIR)/$(TARBALL_NAME); \
	  rm -f $(TARBALL_NAME); \
	fi

