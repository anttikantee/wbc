.PHONY: example

RECIPES=recipes/MarBock.yaml recipes/IPAnema.yaml
README=README.md
RT=${README}.tmp

all:
	@echo you probably do not need to run \"make\"

# (re-)create examples in readme
examples:
	sed '/<!-- BEGIN EXAMPLE -->/q' < ${README} > ${RT}
	for r in ${RECIPES}; do \
		printf 'Example recipe\n---\n```\n' >> ${RT}; \
		cat $${r} >> ${RT}; \
		printf '```\n' >> ${RT}; \
		printf 'translated with `wbctool -P units_output=metric ' \
		    >> ${RT}; \
		printf -- '-P strength_output=plato`:\n```\n' >> ${RT}; \
		PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
		    ./bin/wbctool.py -p ./WBCparams-example \
		    -P units_output=metric -P strength_output=plato \
		    $${r} >> ${RT}; \
		printf '```\n\n' >> ${RT}; \
		printf 'translated with `wbctool -P units_output=us ' >> ${RT};\
		printf -- '-P strength_output=sg`:\n```\n' >> ${RT}; \
		PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
		    ./bin/wbctool.py -p ./WBCparams-example \
		    -P units_output=us -P strength_output=sg $${r} >> ${RT}; \
		printf '```\n\n' >> ${RT} ; done
	mv ${RT} ${README}
