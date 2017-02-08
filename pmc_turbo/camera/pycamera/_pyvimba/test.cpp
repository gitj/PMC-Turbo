//============================================================================
// Name        : test.cpp
// Author      : 
// Version     :
// Copyright   : Your copyright notice
// Description : Hello World in C, Ansi-style
//============================================================================

#include <stdio.h>
#include <stdlib.h>
#include "GigECamera.h"
#include <iostream>

int main(void) {
	puts("Hello World!!!");
	GigECamera *gec = new GigECamera;
	gec->Connect("10.0.0.2",16);
	cout << "buffersize " << gec->buffer_size <<endl;
	uint8_t *data = new uint8_t[3232*4864*2];
	cout << gec->GetImageSimple(data)<<endl;
	cout << gec->GetImageSimple(data)<<endl;
	return EXIT_SUCCESS;
}
