/*
 * GigECamera.cpp
 *
 *  Created on: Aug 2, 2016
 *      Author: gjones
 */

#include <string>
#include <PvDevice.h>
#include <PvDeviceGEV.h>
#include <PvResult.h>
#include <PvString.h>
#include <PvStream.h>
#include <PvStreamGEV.h>
#include <PvPipeline.h>
#include <PvBuffer.h>
#include <iostream>
#include <cstring>

#include "GigECamera.h"

#define BUFFER_COUNT ( 16 )

using namespace std;

GigECamera::GigECamera() {
	buffer_size = 0;
}

void GigECamera::Connect(const char *ip_string) {
	PvResult result = PvResult();
	device = PvDevice::CreateAndConnect(ip_string, &result);

	stream = PvStream::CreateAndOpen(ip_string, &result);
    PvDeviceGEV* lDeviceGEV = dynamic_cast<PvDeviceGEV *>( device );
    if ( lDeviceGEV != NULL )
    {
        PvStreamGEV *lStreamGEV = static_cast<PvStreamGEV *>( stream );

        // Negotiate packet size
        lDeviceGEV->NegotiatePacketSize();

        // Configure device streaming destination
        lDeviceGEV->SetStreamDestination( lStreamGEV->GetLocalIPAddress(), lStreamGEV->GetLocalPort() );
    }

    pipeline = new PvPipeline( stream );

    if ( pipeline != NULL )
    {
        // Reading payload size from device
        uint32_t lSize = device->GetPayloadSize();

        // Set the Buffer count and the Buffer size
        pipeline->SetBufferCount( BUFFER_COUNT );
        pipeline->SetBufferSize( lSize );
        buffer_size = lSize;
    }
    else {
    	cerr << "Could not create pipeline!!!" << endl;
    }

    pipeline->Start();

    parameters = device->GetParameters();
    int n = parameters->GetCount();
	for (int k = 0; k < n; k++) {
		PvGenParameter *p = parameters->Get(k);
		parameter_names.push_back(p->GetName().GetAscii());
		//cout << p->GetName().GetAscii() << endl;
	}

	PvGenCommand *lStart = dynamic_cast<PvGenCommand *>( parameters->Get( "AcquisitionStart" ) );
	PvGenCommand *lStop = dynamic_cast<PvGenCommand *>( parameters->Get( "AcquisitionStop" ) );

	device->StreamEnable();
	lStart->Execute();

}

GigECamera::~GigECamera() {

}

uint32_t GigECamera::GetImage(uint8_t *data){
    PvBuffer *lBuffer = NULL;
    uint32_t actual_size = 0;
    PvResult lOperationResult;
    cout << "in getimage" <<endl;
	PvResult lResult = pipeline->RetrieveNextBuffer( &lBuffer, 1000, &lOperationResult );
	cout << "Got buffer" << endl;
	if ( lResult.IsOK() ) {
		cout << "result ok" <<endl;
		if ( lOperationResult.IsOK() ) {
			cout << "operation ok" <<endl;
			if (lBuffer->GetPayloadType() == PvPayloadTypeImage){
				cout << "is image" << endl;
                PvImage *lImage = lBuffer->GetImage();
                cout << "got image interface" <<  endl;
                actual_size = lImage->GetImageSize();
                cout << "actual size " << actual_size << endl;
                memcpy(data,lImage->GetDataPointer(),buffer_size);
                cout << "memcopy ok" << endl;

			}
		}
		pipeline->ReleaseBuffer(lBuffer);
		cout << "released buffer";
	}
	return actual_size;

}

vector<string> GigECamera::GetParameterNames(void) {
	return parameter_names;
}
uint32_t GigECamera::SetParameterFromString(const char *name, const char *value){
	PvResult result = PvResult();
	PvGenParameter *param = parameters->Get(name);
	result = param->FromString(value);
	return result.GetCode();
}

const char *GigECamera::GetParameter(const char *name){
	PvString result = PvString();
	PvGenParameter *param = parameters->Get(name);
	result = param->ToString();
	return result.GetAscii();
}
//
//int GigECamera::SetParameterInt(const char *name, int value) {
//	PvGenParameter *param = parameters->Get(name);
//	param->FromString()
//}
