/*
 * GigECamera.cpp
 *
 *  Created on: Sep 24, 2016
 *      Author: gjones
 */

#include <string>
#include <iostream>
#include <sstream>
#include <cstring>
#include <cstdlib>

#include "GigECamera.h"

using namespace std;

GigECamera::GigECamera() : m_system ( VimbaSystem::GetInstance() ) {
	buffer_size = 0;
}

uint32_t GigECamera::Connect(const char *ip_string, const uint32_t num_buffers) {
	uint32_t result;
	result = m_system.Startup();
	if(result != VmbErrorSuccess) {
		return result;
	}
	cout << "startup" << endl;
    result = m_system.OpenCameraByID( ip_string, VmbAccessModeFull, m_pCamera );
    if(result != VmbErrorSuccess) {
		return result;
	}
    cout << "open by id" << endl;
    FeaturePtr CommandFeature;
    result = m_pCamera->GetFeatureByName( "GVSPAdjustPacketSize", CommandFeature );
	if ( result != VmbErrorSuccess)
	{
		return result;
	}
	cout << "get adjust feature" <<endl;
    result = CommandFeature->RunCommand();
    if ( result != VmbErrorSuccess)
	{
		return result;
	}
    cout <<"run adjust"<<endl;
	bool IsCommandDone = false;
	do
	{
		if ( VmbErrorSuccess != CommandFeature->IsCommandDone( IsCommandDone ))
		{
			break;
		}
	} while ( false == IsCommandDone );

	cout <<"done adjust" <<endl;
	FeaturePtr FormatFeature;
	// Set pixel format.
	result = m_pCamera->GetFeatureByName( "PixelFormat", FormatFeature );
	if ( result != VmbErrorSuccess)
	{
		return result;
	}
	cout <<"format feature" <<endl;
	result = FormatFeature->SetValue( VmbPixelFormatMono14 );
	if ( result != VmbErrorSuccess)
	{
		return result;
	}

	buffer_size = 3232*4864*2; // TODO: This shouldn't need to be hard coded
	cout <<"image size: " << buffer_size << endl;
	FeaturePtrVector features;
	m_pCamera->GetFeatures(features);
	int n = features.size();
	cout << "get features," << n << endl;
	for (int k = 0; k < n; k++) {
		FeaturePtr p = features.at(k);
		string *name = new string;
		p->GetName(*name);
		parameter_names.push_back(name->c_str());
		delete name;
	}
	IFrameObserverPtr pObserver(new FrameObserver(m_pCamera));
	frame_observer = pObserver;
	return VmbErrorSuccess;


}

GigECamera::~GigECamera() {
	m_system.Shutdown();

}

uint32_t GigECamera::StartCapture() {
	return m_pCamera->StartCapture();
}

uint32_t GigECamera::EndCapture() {
	return m_pCamera->EndCapture();
}

uint32_t GigECamera::GetImageSimple(uint8_t *data){

	uint32_t result;
	FramePtr Frame;
	uint8_t *image;
	result = m_pCamera->AcquireSingleImage( Frame, 5000 );
	if ( result != VmbErrorSuccess)
	{
		return result;
	}
	Frame->GetImageSize(buffer_size);
	Frame->GetImage(image);
	memcpy(data,image,buffer_size);
	return buffer_size;

}


uint32_t GigECamera::QueueFrameFromBuffer(uint8_t *data, frame_info *p_info){
	FramePtr frame(new CustomFrame(data,buffer_size,p_info));
	frame->RegisterObserver(frame_observer);
	//m_pCamera->AnnounceFrame(frame);
	m_pCamera->QueueFrame(frame);
}

uint32_t GigECamera::GetImage(uint8_t *data, uint64_t &frame_id,
		uint64_t &timestamp, uint32_t &frame_status){

	uint32_t result;
	uint32_t this_buffer_size;
	FramePtr Frame;
	uint8_t *image;
	VmbUint64_t v_frame_id;
	VmbUint64_t v_timestamp;
	result = m_pCamera->AcquireSingleImage( Frame, 5000 );
	if ( result != VmbErrorSuccess)
	{
		return result;
	}
	Frame->GetImageSize(this_buffer_size);
//	if(this_buffer_size != buffer_size){
//		cout << "This buffer size is " << this_buffer_size << " not " << buffer_size << endl;
//	}
	Frame->GetImage(image);
	memcpy(data,image,buffer_size);
	Frame->GetFrameID(v_frame_id);
	Frame->GetTimestamp(v_timestamp);
	VmbFrameStatusType v_status;
	Frame->GetReceiveStatus(v_status);
	frame_id = v_frame_id;
	timestamp = v_timestamp;
	frame_status = v_status;
	return this_buffer_size;

}


vector<string> GigECamera::GetParameterNames(void) {
	return parameter_names;
}
uint32_t GigECamera::SetParameterFromString(const char *name, const char *value){
	FeaturePtr feature;
	VmbFeatureDataType datatype;
	uint32_t result = m_pCamera->GetFeatureByName(name,feature);
	if (result != VmbErrorSuccess) {
		return result;
	}
	feature->GetDataType(datatype);
	if ((datatype == VmbFeatureDataString)||
			(datatype == VmbFeatureDataEnum)) {
		return feature->SetValue(value);
	} else if ((datatype == VmbFeatureDataInt)){
		long long int intval;
		intval = strtol(value,NULL,10);
		cout << name << " : " << intval << endl;
		return feature->SetValue(intval);
	} else if (datatype == VmbFeatureDataFloat) {
		double fval;
		fval = strtod(value,NULL);
		cout << name << " : " << fval << endl;
		return feature->SetValue(fval);
	} else {
		cout << "unsupported type: " << datatype << endl;
	}
	return VmbErrorWrongType;
}

uint32_t GigECamera::RunFeatureCommand(const char *name){
	FeaturePtr feature;
	VmbFeatureDataType datatype;
	uint32_t result = m_pCamera->GetFeatureByName(name,feature);
	if (result != VmbErrorSuccess) {
		return result;
	}
	feature->GetDataType(datatype);
	if (datatype != VmbFeatureDataCommand){
		return VmbErrorWrongType;
	}
	return feature->RunCommand();
}


string GigECamera::GetParameter(const char *name){
	FeaturePtr feature;
	string value;
	ostringstream ss;
	VmbFeatureDataType datatype;
	uint32_t result = m_pCamera->GetFeatureByName(name,feature);
	if (result != VmbErrorSuccess) {
		value = string("Error No Such Feature");
		return value;
	}
	feature->GetDataType(datatype);
	if ((datatype == VmbFeatureDataString)||
			(datatype == VmbFeatureDataEnum)) {
		feature->GetValue(value);
	} else if ((datatype == VmbFeatureDataInt)){
		long long int intval;
		feature->GetValue(intval);
		ss << intval;
		cout << intval << endl;
		value = ss.str();
	} else if (datatype == VmbFeatureDataFloat) {
		double fval;
		feature->GetValue(fval);
		ss << fval;
		cout << fval << endl;
		value = ss.str();
	} else {
		cout << "unsupported type: " << datatype << endl;
	}
	cout << name << ":" << value << endl;
	return value;
}

FrameObserver::FrameObserver(CameraPtr pCamera) : IFrameObserver(pCamera)
{
	cout << "Hi from frame observer" << endl;
}
void FrameObserver::FrameReceived(const FramePtr pFrame)
{
	VmbUint64_t frame_id;
	pFrame->GetFrameID(frame_id);
	VmbUint64_t timestamp;
	pFrame->GetTimestamp(timestamp);
	CustomFrame *cframe = static_cast<CustomFrame *>(SP_ACCESS(pFrame));
	cframe->info->frame_id = frame_id;
	cframe->info->timestamp = timestamp;
	VmbFrameStatusType frame_status;
	pFrame->GetReceiveStatus(frame_status);
	cframe->info->frame_status = frame_status;
	cframe->info->is_filled = 1;
	cout << "got frame " << frame_id << " ts: " << timestamp << " id: " << cframe->info->frame_id<< endl;
	//m_pCamera->QueueFrame(pFrame);
	delete pFrame.get();
}

CustomFrame::CustomFrame(VmbUchar_t *pBuffer, VmbInt64_t bufferSize , frame_info *p_info) : Frame(pBuffer, bufferSize)
{
	info = p_info;
	info->is_filled = 0;
}

