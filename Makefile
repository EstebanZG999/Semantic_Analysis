DOCKER_IMAGE := csp-image
PROJECT_ROOT := $(PWD)
PROGRAM_DIR  := $(PWD)/program

# Montamos tpdo el repo en /workspace
DOCKER_RUN   := docker run --rm -ti -u $(shell id -u):$(shell id -g) \
  -v "$(PROJECT_ROOT)":/workspace -w /workspace $(DOCKER_IMAGE)

.PHONY: docker-build gen run test clean

docker-build:
	docker build --rm . -t $(DOCKER_IMAGE)

# Genera lexer/parser/visitor con ANTLR dentro del contenedor
gen: docker-build
	$(DOCKER_RUN) bash -lc 'cd program && antlr -Dlanguage=Python3 -visitor Compiscript.g4 && ls -1 Compiscript*.py'

# Ejecuta el driver dentro del contenedor
run: docker-build
	$(DOCKER_RUN) python3 program/Driver.py program/program.cps

# Corre pytest dentro del contenedor
test: docker-build
	$(DOCKER_RUN) bash -lc 'python3 -m pip install -q --break-system-packages pytest && PYTHONPATH=/workspace pytest -q'

# Limpia artefactos generados por ANTLR en tu árbol local
clean:
	@find program -maxdepth 1 -type f \( \
		-name "Compiscript*.py" -o -name "Compiscript*.tokens" -o -name "Compiscript*.interp" \
	\) -print -delete
