# PrIC3

Probabilistic IC3: A prototype implementation of [PrIC3: Property Directed Reachability for MDPs](cav_artifact/paper.pdf).

## CAV Artifact Docker Image

You can experiment with PrIC3 in a convenient Docker image, as was provided for the CAV submission.

Build the Docker image: `docker build -t pric3 -f cav_artifact/Dockerfile .`

More information can be found in [`cav_artifact/README.md`](cav_artifact/README.md).

## Development

* Run tests with [`pytest`](https://docs.pytest.org/en/latest/): Just execute `make test` in this directory (or `pytest --doctest-modules -v` for more details).
* We use the [`yapf`](https://github.com/google/yapf) formatter: `yapf --recursive -i pric3/` and `isort`.

### Building API Documentation

You'll need `sphinx`: `pip3 install sphinx`.

1. To build the documentation: `make docs`.
2. Then view the documentation in `docs/build/html/index.html`.

To add new modules to the documentation, edit `docs/source/index.rst` accordingly.
