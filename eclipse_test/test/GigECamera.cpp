/*
 * GigECamera.cpp
 *
 *  Created on: Aug 2, 2016
 *      Author: gjones
 */

#include <string>
#include <PvDevice.h>
#include <PvResult.h>
#include <PvString.h>
#include <iostream>
#include "GigECamera.h"

using namespace std;

GigECamera::GigECamera() {
}

void GigECamera::Connect(const char *ip_string) {
	PvResult result = PvResult();
	device = PvDevice::CreateAndConnect(ip_string, &result);
	parameters = device->GetParameters();
	int n = parameters->GetCount();
	for (int k = 0; k < n; k++) {
		PvGenParameter *p = parameters->Get(k);
		parameter_names.push_back(p->GetName().GetAscii());
		cout << p->GetName().GetAscii() << endl;
	}
}

GigECamera::~GigECamera() {

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
