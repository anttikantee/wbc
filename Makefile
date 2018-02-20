.PHONY: example

RECIPE=recipes/MarBock.yaml
README=README.md
RT=${README}.tmp

all:
	@echo you probably do not need to run \"make\"

# (re-)create example in readme
example:
	sed '/<!-- BEGIN EXAMPLE -->/q' < ${README} > ${RT}
	printf 'recipe:\n```\n' >> ${RT}
	cat ${RECIPE} >> ${RT}
	printf '```\ntranslated with `wbctool -u metric -u plato`:\n```\n' >> ${RT}
	PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
	    ./bin/wbctool.py -u metric -u plato ${RECIPE} >> ${RT}
	printf '```\n\n' >> ${RT}
	printf 'translated with `wbctool -u us -u sg`:\n```\n' >> ${RT}
	PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
	    ./bin/wbctool.py -u us -u sg ${RECIPE} >> ${RT}
	printf '```\n' >> ${RT}
	mv ${RT} ${README}
