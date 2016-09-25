/*
 * GigECamera.h
 *
 *  Created on: Aug 2, 2016
 *      Author: gjones
 */

#ifndef GIGECAMERA_H_
#define GIGECAMERA_H_

#include <vector>
#include <string>
#include <stdint.h>
#include "VimbaCPP/Include/VimbaCPP.h"

using namespace std;
using namespace AVT::VmbAPI;

class GigECamera {
public:
	GigECamera();
	~GigECamera();
	uint32_t Connect(const char *ip_string, const uint32_t num_buffers);
	vector<string> GetParameterNames();
	uint32_t SetParameterFromString(const char *name, const char *value);
	uint32_t RunFeatureCommand(const char *name);
	const char *GetParameter(const char *name);
	uint32_t GetImageSimple(uint8_t *data);
	uint32_t GetImage(uint8_t *data, uint64_t &frame_id,
			uint64_t &timestamp);
/*	uint32_t GetImage(uint8_t *data, uint64_t &block_id,
			uint64_t &buffer_id, uint64_t &reception_time,
			uint64_t &timestamp, uint32_t &result_code,
			uint32_t &operation_code);
	//void GetBuffer(PvBuffer * output);
	 */
	uint32_t buffer_size;
private:
	// A reference to the Vimba singleton
	VimbaSystem &m_system;
    CameraPtr m_pCamera;
	vector<string> parameter_names;
};


#endif /* GIGECAMERA_H_ */

