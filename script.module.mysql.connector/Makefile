addon_xml = addon.xml

# Collect information to build as sensible package name
name = $(shell xmllint --xpath 'string(/addon/@id)' $(addon_xml))
version = $(shell xmllint --xpath 'string(/addon/@version)' $(addon_xml))
git_branch = $(shell git rev-parse --abbrev-ref HEAD)
git_hash = $(shell git rev-parse --short HEAD)

zip_name = $(name)-$(version)-$(git_branch)-$(git_hash).zip
include_files = addon.xml icon.png LICENSE.txt README.rst lib/
include_paths = $(patsubst %,$(name)/%,$(include_files))
exclude_files = \*.new \*.orig \*.pyc \*.pyo
zip_dir = $(name)/

blue = \e[1;34m
white = \e[1;37m
reset = \e[0m

all: zip

addon: clean
	@echo -e "$(white)=$(blue) Starting sanity addon tests$(reset)"
	kodi-addon-checker . --branch=leia

zip:
	@echo -e "\e[1;37m=\e[1;34m Building new package\e[0m"
	rm -f ../$(zip_name)
	cd ..; zip -r $(zip_name) $(name) -x $(exclude_paths)
	@echo -e "\e[1;37m=\e[1;34m Successfully wrote package as: \e[1;37m../$(zip_name)\e[0m"

zip: clean
	@echo -e "$(white)=$(blue) Building new package$(reset)"
	@rm -f ../$(zip_name)
	cd ..; zip -r $(zip_name) $(include_paths) -x $(exclude_files)
	@echo -e "$(white)=$(blue) Successfully wrote package as: $(white)../$(zip_name)$(reset)"

clean:
	find . -name '*.pyc' -type f -delete
	find . -name '__pycache__' -type d -delete
	rm -rf .pytest_cache/
