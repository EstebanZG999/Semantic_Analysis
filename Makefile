DOCKER_IMAGE := csp-image
PROGRAM_DIR  := $(PWD)/program
# corre el contenedor
DOCKER_RUN   := docker run --rm -ti -u $(shell id -u):$(shell id -g) -v "$(PROGRAM_DIR)":/program $(DOCKER_IMAGE)

.PHONY: docker-build gen run test clean

docker-build:
	docker build --rm . -t $(DOCKER_IMAGE)

# Genera lexer/parser/visitor con ANTLR dentro del contenedor
gen: docker-build
	$(DOCKER_RUN) bash -lc 'cd /program && antlr -Dlanguage=Python3 -visitor Compiscript.g4 && ls -1 Compiscript*.py'

# Ejecuta el driver dentro del contenedor
run: docker-build
	$(DOCKER_RUN) python3 /program/Driver.py /program/program.cps

# Corre pytest dentro del contenedor
test: docker-build
	$(DOCKER_RUN) bash -lc 'python3 -m pip install -q pytest && cd /program && pytest -q || true'

# Limpia artefactos generados por ANTLR
clean:
	@find program -maxdepth 1 -type f \( \
		-name "Compiscript*.py" -o -name "Compiscript*.tokens" -o -name "Compiscript*.interp" \
	\) -print -delete