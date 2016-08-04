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
#include <iostream>

int main(void) {
	puts("Hello World!!!");
	GigECamera *gec = new GigECamera;
	gec->Connect("10.0.0.2",16);
	cout << "buffersize " << gec->buffer_size <<endl;
	uint8_t *data = new uint8_t[gec->buffer_size];
	cout << gec->GetImage(data,true);
	return EXIT_SUCCESS;
}
