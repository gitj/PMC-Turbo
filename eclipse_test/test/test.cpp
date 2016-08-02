//============================================================================
// Name        : test.cpp
// Author      : 
// Version     :
// Copyright   : Your copyright notice
// Description : Hello World in C, Ansi-style
//============================================================================

#include <stdio.h>
#include <stdlib.h>
//#include <PvDevice.h>
//#include <PvResult.h>
//#include <PvString.h>
#include "GigECamera.h"

int main(void) {
	puts("Hello World!!!");
	GigECamera *gec = new GigECamera;
	gec->Connect("10.0.0.2");
	return EXIT_SUCCESS;
}
