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
#include <PvStream.h>
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
	uint32_t GetImage(uint8_t *data);
	uint32_t buffer_size;
private:
	PvDevice *device;
	PvGenParameterArray *parameters;
	PvStream *stream;
	vector<string> parameter_names;
	PvPipeline *pipeline;
};


#endif /* GIGECAMERA_H_ */

