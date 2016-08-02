/*
 * GigECamera.h
 *
 *  Created on: Aug 2, 2016
 *      Author: gjones
 */

#ifndef GIGECAMERA_H_
#define GIGECAMERA_H_

#include <PvDevice.h>
#include <PvGenParameterArray.h>
#include <vector>
#include <string>

using namespace std;

class GigECamera {
public:
	GigECamera();
	~GigECamera();
	void Connect(const char *ip_string);
	vector<string> GetParameterNames();
	uint32_t SetParameterFromString(const char *name, const char *value);
	const char *GetParameter(const char *name);
private:
	PvDevice *device;
	PvGenParameterArray *parameters;
	vector<string> parameter_names;
};


#endif /* GIGECAMERA_H_ */

