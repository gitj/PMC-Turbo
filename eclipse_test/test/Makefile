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

PUREGEV_ROOT        ?= ../../..
PV_LIBRARY_PATH      =$(PUREGEV_ROOT)/lib

CFLAGS              += -I$(PUREGEV_ROOT)/include -I. -I/usr/include/python
CPPFLAGS            += -I$(PUREGEV_ROOT)/include -I. -fPIC -I/usr/include/python2.7
ifdef _DEBUG
    CFLAGS    += -g -D_DEBUG
    CPPFLAGS  += -g -D_DEBUG
else
    CFLAGS    += -O3
    CPPFLAGS  += -O3
endif
CFLAGS    += -D_UNIX_ -D_LINUX_
CPPFLAGS  += -D_UNIX_ -D_LINUX_

LDFLAGS             += -L$(PUREGEV_ROOT)/lib         \
                        -lPvBase                     \
                        -lPvDevice                   \
                        -lPvBuffer                   \
                        -lPvGenICam                  \
                        -lPvStream                   \
                        -lPvTransmitter              \
                        -lPvVirtualDevice	         \
		                -lPvAppUtils                 \
                        -lPvPersistence              \
                        -lPvSerial



# Conditional linking and usage of the GUI on the sample only when available
ifeq ($(wildcard $(PUREGEV_ROOT)/lib/libPvGUI.so),)
    CFLAGS    += -DPV_GUI_NOT_AVAILABLE
    CPPFLAGS  += -DPV_GUI_NOT_AVAILABLE
else
    LDFLAGS   += -lPvGUI
endif 

# Add simple imaging lib to the linker options only if available
ifneq ($(wildcard $(PUREGEV_ROOT)/lib/libSimpleImagingLib.so),)
    LDFLAGS   += -lSimpleImagingLib
endif 

# Configure Genicam
GEN_LIB_PATH = $(PUREGEV_ROOT)/lib/genicam/bin/Linux64_x64
LDFLAGS      += -L$(GEN_LIB_PATH)


LD_LIBRARY_PATH       = $(PV_LIBRARY_PATH):$(GEN_LIB_PATH)
export LD_LIBRARY_PATH

OBJS      += $(SRC_CPPS:%.cpp=%.o)
OBJS      += $(SRC_CS:%.c=%.o)

all: $(EXEC) lib

lib: pycamera.so

clean:
	rm -rf $(OBJS) $(EXEC) pycamera.cpp pycamera.o *.so

.SECONDARY:

pycamera.cpp: pycamera.pyx
	cython --cplus -o $@ $^

%.o: %.cxx
	$(CXX) -c $(CPPFLAGS) -o $@ $<

%.o: %.cpp
	$(CXX) -c $(CPPFLAGS) -o $@ $<

%.o: %.c
	$(CC) -c $(CFLAGS) -o $@ $<

%.so: $(OBJS) pycamera.o
	$(CXX) -shared -fPIC $(LDFLAGS) -o $@ $(OBJS) pycamera.o

$(EXEC): $(OBJS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS) 

.PHONY: all lib clean