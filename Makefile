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
		printf '```\ntranslated with `wbctool -u metric -u plato`:\n```\n' >> ${RT}; \
		PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
		    ./bin/wbctool.py -u metric -u plato $${r} >> ${RT}; \
		printf '```\n\n' >> ${RT}; \
		printf 'translated with `wbctool -u us -u sg`:\n```\n' \
		    >> ${RT}; \
		PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
		    ./bin/wbctool.py -u us -u sg $${r} >> ${RT}; \
		printf '```\n\n' >> ${RT} ; done
	mv ${RT} ${README}
