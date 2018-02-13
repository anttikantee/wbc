.PHONY: example

RECIPE=recipes/MarBock.yaml
README=README.md
RT=${README}.tmp

all:
	@echo you probably do not need to run \"make\"

# (re-)create example in readme
example:
	sed '/<!-- BEGIN EXAMPLE -->/q' < ${README} > ${RT}
	printf 'recipe:\n```\n\n' >> ${RT}
	cat ${RECIPE} >> ${RT}
	printf '```\n\ntranslated with `wbctool`:\n\n```\n' >> ${RT}
	PYTHONPATH=. python ./bin/wbctool.py ${RECIPE} >> ${RT}
	printf '```\n' >> ${RT}
	mv ${RT} ${README}
