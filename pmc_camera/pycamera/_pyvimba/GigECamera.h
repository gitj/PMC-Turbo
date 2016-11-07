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

struct frame_info {
	uint64_t frame_id;
	uint64_t timestamp;
	uint32_t frame_status;
	uint32_t is_filled;
} __attribute__((packed));

class GigECamera{
public:
	GigECamera();
	~GigECamera();
	uint32_t Connect(const char *ip_string, const uint32_t num_buffers);
	uint32_t StartCapture();
	uint32_t EndCapture();
	vector<string> GetParameterNames();
	uint32_t SetParameterFromString(const char *name, const char *value);
	uint32_t RunFeatureCommand(const char *name);
	string GetParameter(const char *name);
	uint32_t GetImageSimple(uint8_t *data);
	uint32_t GetImage(uint8_t *data, uint64_t &frame_id,
			uint64_t &timestamp, uint32_t &frame_status);
	uint32_t QueueFrameFromBuffer(uint8_t *data, uint32_t size, frame_info *p_info);
	uint32_t buffer_size;
private:
	// A reference to the Vimba singleton
	VimbaSystem &m_system;
    CameraPtr m_pCamera;
	vector<string> parameter_names;
	IFrameObserverPtr frame_observer;
};

class FrameObserver : public IFrameObserver
{
public:
	FrameObserver(CameraPtr pCamera);
	void FrameReceived(FramePtr pFrame );
};


class CustomFrame : public Frame
{
public:
	CustomFrame(VmbUchar_t *pBuffer, VmbInt64_t bufferSize, frame_info *p_info );
	frame_info *info;
};

#endif /* GIGECAMERA_H_ */


