# pylint: disable-all
import inspect
import os
import sys
from datetime import datetime

import graphviz
import sphinx_bootstrap_theme
import z3

import stormpy

sys.path.insert(0, os.path.abspath('../..'))

extensions = [
    'sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.mathjax',
    'sphinx.ext.intersphinx', 'sphinx.ext.viewcode', 'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints', 'sphinx.ext.autosummary', 'sphinx.ext.doctest',
    'sphinx_click.ext', 'sphinx_git'
]

# General information about the project.
project = 'PrIC3'
copyright = '{}, Philipp Schroer'.format(datetime.now().year) # TODO
author = 'Philipp Schroer'
master_doc = 'index'
pygments_style = 'sphinx'
todo_include_todos = True

html_theme_path = ["themes"] + sphinx_bootstrap_theme.get_html_theme_path()
html_theme = 'fixedbootstrap'
_navbar_links = [('GitHub', 'https://github.com/KevinBatz/PrIC3/', True),
                 ('GitLab',
                  'https://git.rwth-aachen.de/philipp.schroer/pric3/', True)]
html_theme_options = {
    'navbar_sidebarrel': False,
    'globaltoc_depth': -1,
    'navbar_site_name': "Contents",
    'source_link_position': "footer",
    'bootswatch_theme': "united",
    'navbar_pagenav': False,
    'navbar_links': _navbar_links
}
html_static_path = ['_static']

template_path = ['_templates']
html_sidebars = {'**': ['simpletoctree.html']}

# Why is all this explicitness needed? :(
autodoc_default_options = {'members': True, 'undoc-members': True}
autodoc_member_order = "bysource"

#napoleon_use_ivar = True

# et typing.TYPE_CHECKING to True to enable “expensive” typing imports
set_type_checking_flag = True
always_document_param_types = True

intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

# Annotation Formatting Hacks
# ---------------------------
#
# We fix two bugs in the annotation formatting of sphinx_autodoc_typehints:
#   1. re-exported annotations don't get linked properly. We try to detect specific cases for some of our deps.
#   2. newtypes are formatted weirdly. Instead of "NewType(StateId, int)", we just print "StateId".

module_overrides = {
    cls.__module__: module.__name__
    for module in [stormpy, z3, graphviz] for _, cls in module.__dict__.items()
    if isinstance(cls, type) and cls.__module__.startswith(module.__name__)
}


def _handle_reexported_annotation(annotation):
    if isinstance(annotation, type):
        module_override = module_overrides.get(annotation.__module__)
        if module_override is not None:
            return f':py:class:`~{module_override}.{annotation.__qualname__}`'


def _handle_newtype_annotation(annotation):
    if inspect.isfunction(
            annotation) and annotation.__module__ == 'typing' and hasattr(
                annotation, '__name__') and hasattr(annotation,
                                                    '__supertype__'):
        module = f'{annotation.declaration_module_name}.' if hasattr(
            annotation, 'declaration_module_name') else ''
        return ':py:data:`~{module}{name}`'.format(module=module,
                                                   name=annotation.__name__)


def _override_format_annotation():
    import sphinx_autodoc_typehints

    _format_annotation = sphinx_autodoc_typehints.format_annotation

    def format_annotation(annotation, *more_pos_args, **more_key_args):
        return _handle_reexported_annotation(
            annotation) or _handle_newtype_annotation(
                annotation) or _format_annotation(annotation, *more_pos_args,
                                                  **more_key_args)

    sphinx_autodoc_typehints.format_annotation = format_annotation


_override_format_annotation()
