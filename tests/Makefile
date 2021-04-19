LEGOS= $(wildcard legos/*.yaml)

tests: compiled-recipes/.timestamp

compiled-recipes/.timestamp: ${LEGOS}
	sh maketestrecipes.sh
	touch $@
