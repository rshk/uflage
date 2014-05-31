.PHONY: all check flake8


all:
	@echo "You must specify a target"
	@echo "check - Run tests"
	@echo "flake8 - Run flake8 on sources"

check:
	py.test -vvv -rsxX ./tests


flake8:
	flake8 ./uflage/ ./tests/
