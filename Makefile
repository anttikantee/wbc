.PHONY: example

RECIPES=MarBock IPAnema
README=README.md
RT=${README}.tmp

all:
	@echo you probably do not need to run \"make\"

# (re-)create examples in readme
examples:
	sed '/<!-- BEGIN EXAMPLE -->/q' < ${README} > ${RT}
	for r in ${RECIPES:%=example-recipes/%.yaml}; do \
		printf 'Example recipe\n---\n```\n' >> ${RT}; \
		cat $${r} >> ${RT}; \
		printf '```\n' >> ${RT}; \
		printf 'translated with `wbcrecipe -P units_output=metric ' \
		    >> ${RT}; \
		printf -- '-P strength_output=plato`:\n```\n' >> ${RT}; \
		PYTHONPATH=. python3 \
		    ./bin/wbcrecipe.py -p ./WBCparams-example \
		    -P units_output=metric -P strength_output=plato \
		    $${r} >> ${RT}; \
		printf '```\n\n' >> ${RT}; \
		printf 'translated with `wbcrecipe -P units_output=us '>>${RT};\
		printf -- '-P strength_output=sg`:\n```\n' >> ${RT}; \
		PYTHONPATH=. python3 \
		    ./bin/wbcrecipe.py -p ./WBCparams-example \
		    -P units_output=us -P strength_output=sg $${r} >> ${RT}; \
		printf '```\n\n' >> ${RT} ; done
	mv ${RT} ${README}
