import warnings as _warnings
try:
    from pycamera.pycamera import PyCamera
except ImportError:
    _warnings.warn("Could not import PyCamera")