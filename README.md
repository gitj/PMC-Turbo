# PMC-Turbo

Proposed structure:

- camera
 - src
 - tests
- flight-control
 - src
 - tests
- lidar
 - src
 - tests
- integration-tests 


For Qt5 to work on Debian 8 Jessie, need to do:
  export QT_XKB_CONFIG_ROOT=/usr/share/X11/xkb/
  export XKB_DEFAULT_RULES=base

The firt one is needed to get the keyboard to work at all, the second gets arrow keys working

see: http://stackoverflow.com/questions/26974644/no-keyboard-input-in-qt-creator-after-update-to-qt5