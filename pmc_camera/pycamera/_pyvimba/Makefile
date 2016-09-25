# Parameters
# SRC_CS: The source C files to compie
# SRC_CPPS: The source CPP files to compile
# EXEC: The executable name

SRC_CS = 
SRC_CPPS = test.cpp GigECamera.cpp
EXEC = test

ifeq ($(SRC_CS) $(SRC_CPPS),)
  $(error No source files specified)
endif

ifeq ($(EXEC),)
  $(error No executable file specified)
endif

CC                  ?= gcc
CXX                 ?= g++



VIMBA_ROOT	        ?= /home/pmc/pmchome/Vimba_2_0
VIMBA_LIBRARY_PATH      =$(VIMBA_ROOT)/lib

#Compile options needed for VimbaC
VIMBAC_CFLAGS   = -I$(VIMBA_ROOT)

#Linker options needed for VimbaC
VIMBAC_LIBS     = -L. -lVimbaCPP -lVimbaC

#By default we copy libVimbaC.so next to the binary
libVimbaC.so: 
	cp $(VIMBA_ROOT)/VimbaC/DynamicLib/x86_64bit/libVimbaC.so .
libVimbaCPP.so: 
	cp $(VIMBA_ROOT)/VimbaCPP/DynamicLib/x86_64bit/libVimbaCPP.so .

CFLAGS              += $(VIMBAC_CFLAGS) -I. -I/usr/include/python
CPPFLAGS            += $(VIMBAC_CFLAGS) -I. -fPIC -I/usr/include/python2.7
ifdef _DEBUG
    CFLAGS    += -g -D_DEBUG
    CPPFLAGS  += -g -D_DEBUG
else
    CFLAGS    += -O3
    CPPFLAGS  += -O3
endif
CFLAGS    += -D_UNIX_ -D_LINUX_
CPPFLAGS  += -D_UNIX_ -D_LINUX_

LDFLAGS             += $(VIMBAC_LIBS)

OBJS      += $(SRC_CPPS:%.cpp=%.o)
OBJS      += $(SRC_CS:%.c=%.o)

all: $(EXEC)# lib

lib: libVimbaCPP.so libVimbaC.so _pyvimba.so 

clean:
	rm -rf $(OBJS) $(EXEC) _pyvimba.cpp _pyvimba.o *.so

.SECONDARY:

_pyvimba.cpp: _pyvimba.pyx
	cython --cplus -o $@ $^

%.o: %.cxx
	$(CXX) -c $(CPPFLAGS) -o $@ $<

%.o: %.cpp
	$(CXX) -c $(CPPFLAGS) -o $@ $<

%.o: %.c
	$(CC) -c $(CFLAGS) -o $@ $<

%.so: $(OBJS) %.o
	$(CXX) -shared -fPIC $(LDFLAGS) -o $@ $(OBJS) _pyvimba.o

$(EXEC): $(OBJS) libVimbaCPP.so libVimbaC.so
	$(CXX) $(OBJS) -o $@ $(LDFLAGS) 

.PHONY: all lib clean