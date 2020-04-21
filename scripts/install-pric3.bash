set -e # fail on errors

if [[ "$VIRTUAL_ENV" == "" ]]; then
  source env_python/bin/activate
fi

apt-get install -y graphviz
pip3 install click pysmt pytest graphviz sphinx sphinx-click sphinx-bootstrap-theme sphinx_autodoc_typehints sphinx-git mypy pylint pandas
yes Y | pysmt-install --z3

apt-get install -y latexmk texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra

# install the actual package
pip3 install -ve .
