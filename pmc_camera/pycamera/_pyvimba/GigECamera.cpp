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
//		cout << k <<endl;
		p->GetName(*name);
//		cout << "got name" << endl;
		parameter_names.push_back(name->c_str());
//		cout << *name << endl;
		delete name;
		//cout << p->GetName().GetAscii() << endl;
	}
	return VmbErrorSuccess;


}

GigECamera::~GigECamera() {
	m_system.Shutdown();

}
/*
uint32_t GigECamera::GetImage(uint8_t *data, uint64_t &block_id,
			uint64_t &buffer_id, uint64_t &reception_time,
			uint64_t &timestamp, uint32_t &result_code,
			uint32_t &operation_code){
}
*/

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

uint32_t GigECamera::GetImage(uint8_t *data, uint64_t &frame_id,
		uint64_t &timestamp){

	uint32_t result;
	FramePtr Frame;
	uint8_t *image;
	VmbUint64_t v_frame_id;
	VmbUint64_t v_timestamp;
	result = m_pCamera->AcquireSingleImage( Frame, 5000 );
	if ( result != VmbErrorSuccess)
	{
		return result;
	}
	Frame->GetImageSize(buffer_size);
	Frame->GetImage(image);
	memcpy(data,image,buffer_size);
	Frame->GetFrameID(v_frame_id);
	Frame->GetTimestamp(v_timestamp);
	frame_id = v_frame_id;
	timestamp = v_timestamp;
	return buffer_size;

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
		feature->SetValue(value);
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


const char *GigECamera::GetParameter(const char *name){
	FeaturePtr feature;
	string value;
	ostringstream ss;
	VmbFeatureDataType datatype;
	uint32_t result = m_pCamera->GetFeatureByName(name,feature);
	if (result != VmbErrorSuccess) {
		value = string("Error No Such Feature");
		return value.c_str();
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
	return value.c_str();
}


//
//int GigECamera::SetParameterInt(const char *name, int value) {
//	PvGenParameter *param = parameters->Get(name);
//	param->FromString()
//}
