"""
.. include:: ../README.md
"""

from .algebra import *
from .basic_math import *
from .calculus import *
from .computer_science import *
from .geometry import *
from .misc import *
from .statistics import *

from ._gen_list import gen_list


# [funcname, subjectname]
def get_gen_list():
    return gen_list


def gen_by_name(name, *args, **kwargs):
    return globals()[name](*args, **kwargs)
