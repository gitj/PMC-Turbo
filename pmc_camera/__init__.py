import warnings as _warnings
from birger import Birger
try:
    from pycamera.pycamera import PyCamera
except ImportError:
    _warnings.warn("Could not import PyCamera")