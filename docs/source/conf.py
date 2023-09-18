# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from __future__ import absolute_import
from docutils import nodes
from docutils.parsers.rst import Directive, directives
import os
import sys


project = 'Action Recorder'
copyright = '2023, InamuraJIN, RivinHD'
author = 'InamuraJIN, RivinHD'
release = '4.0.8'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'myst_parser'
]

templates_path = ['_templates']
exclude_patterns = []

print(os.path.abspath("../../"))
sys.path.insert(0, os.path.abspath("../../"))
napoleon_google_docstring = True
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "attrs_inline"
]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_context = {
   "default_mode": "auto"
}


# Video Embedded
# -*- coding: utf-8 -*-
# From https://gist.github.com/dbrgn/2922648
"""
    ReST directive for embedding Youtube and Vimeo videos.
    There are two directives added: ``youtube`` and ``vimeo``. The only
    argument is the video id of the video to include.
    Both directives have three optional arguments: ``height``, ``width``
    and ``align``. Default height is 281 and default width is 500.
    Example::
        .. youtube:: anwy2MPT5RE
            :height: 315
            :width: 560
            :align: left
    :copyright: (c) 2012 by Danilo Bargen.
    :license: BSD 3-clause
"""


def align(argument):
    """Conversion function for the "align" option."""
    return directives.choice(argument, ('left', 'center', 'right'))


class IframeVideo(Directive):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'height': directives.nonnegative_int,
        'width': directives.nonnegative_int,
        'align': align,
    }
    default_width = 500
    default_height = 281

    def run(self):
        self.options['video_id'] = directives.uri(self.arguments[0])
        if not self.options.get('width'):
            self.options['width'] = self.default_width
        if not self.options.get('height'):
            self.options['height'] = self.default_height
        if not self.options.get('align'):
            self.options['align'] = 'left'
        return [nodes.raw('', self.html % self.options, format='html')]


class Youtube(IframeVideo):
    html = '<iframe src="https://www.youtube.com/embed/%(video_id)s" \
    width="%(width)u" height="%(height)u" frameborder="0" \
    webkitAllowFullScreen mozallowfullscreen allowfullscreen \
    class="align-%(align)s"></iframe>'


class Vimeo(IframeVideo):
    html = '<iframe src="https://player.vimeo.com/video/%(video_id)s" \
    width="%(width)u" height="%(height)u" frameborder="0" \
    webkitAllowFullScreen mozallowfullscreen allowFullScreen \
    class="align-%(align)s"></iframe>'


def setup(builder):
    directives.register_directive('youtube', Youtube)
    directives.register_directive('vimeo', Vimeo)
