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
	printf '```\ntranslated with `wbctool`:\n```\n' >> ${RT}
	PYTHONPATH=. PYTHONIOENCODING=utf-8 python \
	    ./bin/wbctool.py ${RECIPE} >> ${RT}
	printf '```\n' >> ${RT}
	mv ${RT} ${README}
