// *****************************************************************************
//
//      Copyright (c) 2013, Pleora Technologies Inc., All rights reserved.
//
// *****************************************************************************

//
// Shows how to use a PvStream object to acquire images from a GigE Vision or
// USB3 Vision device.
//

#include <PvSampleUtils.h>
#include <PvDevice.h>
#include <PvDeviceGEV.h>
#include <PvDeviceU3V.h>
#include <PvStream.h>
#include <PvStreamGEV.h>
#include <PvStreamU3V.h>
#include <PvBuffer.h>
#include <PvBufferWriter.h>

#include <sstream>
#include <PvSystem.h>
#include <math.h>

#include <list>
typedef std::list<PvBuffer *> BufferList;

PV_INIT_SIGNAL_HANDLER();

#define BUFFER_COUNT ( 16 )

///
/// Function Prototypes
///
const PvDeviceInfo *SelectDevice( PvSystem *aPvSystem );
PvDevice *ConnectToDevice( const PvDeviceInfo *aDeviceInfo );
PvStream *OpenStream( const PvDeviceInfo *aDeviceInfo );
void ConfigureStream( PvDevice *aDevice, PvStream *aStream );
void CreateStreamBuffers( PvDevice *aDevice, PvStream *aStream, BufferList *aBufferList );
void AcquireImages( PvDevice *aDevice, PvStream *aStream );
void FreeStreamBuffers( BufferList *aBufferList );

//
// Main function
//
int main()
{
    const PvDeviceInfo *lDeviceInfo = NULL;
    PvDevice *lDevice = NULL;
    PvStream *lStream = NULL;
    BufferList lBufferList;

    PV_SAMPLE_INIT();

    PvSystem *lPvSystem = new PvSystem;
    lDeviceInfo = SelectDevice( lPvSystem );

    cout << "PvStreamSample:" << endl << endl;

    if ( NULL != lDeviceInfo )
    {
        lDevice = ConnectToDevice( lDeviceInfo );
        if ( NULL != lDevice )
        {
            lStream = OpenStream( lDeviceInfo );
            if ( NULL != lStream )
            {
                ConfigureStream( lDevice, lStream );
                CreateStreamBuffers( lDevice, lStream, &lBufferList );
                AcquireImages( lDevice, lStream );
                FreeStreamBuffers( &lBufferList );
                
                // Close the stream
                cout << "Closing stream" << endl;
                lStream->Close();
                PvStream::Free( lStream );    
            }

            // Disconnect the device
            cout << "Disconnecting device" << endl;
            lDevice->Disconnect();
            PvDevice::Free( lDevice );
        }
    }

    cout << endl;
    cout << "<press a key to exit>" << endl;
    PvWaitForKeyPress();

    if( NULL != lPvSystem )
    {
        delete lPvSystem;
        lPvSystem = NULL;
    }

    PV_SAMPLE_TERMINATE();

    return 0;
}

const PvDeviceInfo *SelectDevice( PvSystem *aPvSystem )
{
    const PvDeviceInfo *lDeviceInfo = NULL;
    PvResult lResult;

    if (NULL != aPvSystem)
    {
        // Get the selected device information.
        lDeviceInfo = PvSelectDevice( *aPvSystem );
    }

    return lDeviceInfo;
}

PvDevice *ConnectToDevice( const PvDeviceInfo *aDeviceInfo )
{
    PvDevice *lDevice;
    PvResult lResult;

    // Connect to the GigE Vision or USB3 Vision device
    cout << "Connecting to " << aDeviceInfo->GetDisplayID().GetAscii() << "." << endl;
    lDevice = PvDevice::CreateAndConnect( aDeviceInfo, &lResult );
    if ( lDevice == NULL )
    {
        cout << "Unable to connect to " << aDeviceInfo->GetDisplayID().GetAscii() << "." << endl;
    }

    return lDevice;
}

PvStream *OpenStream( const PvDeviceInfo *aDeviceInfo )
{
    PvStream *lStream;
    PvResult lResult;

    // Open stream to the GigE Vision or USB3 Vision device
    cout << "Opening stream to device." << endl;
    lStream = PvStream::CreateAndOpen( aDeviceInfo->GetConnectionID(), &lResult );
    if ( lStream == NULL )
    {
        cout << "Unable to stream from " << aDeviceInfo->GetDisplayID().GetAscii() << "." << endl;
    }

    return lStream;
}

void ConfigureStream( PvDevice *aDevice, PvStream *aStream )
{
    // If this is a GigE Vision device, configure GigE Vision specific streaming parameters
    PvDeviceGEV* lDeviceGEV = dynamic_cast<PvDeviceGEV *>( aDevice );
    if ( lDeviceGEV != NULL )
    {
        PvStreamGEV *lStreamGEV = static_cast<PvStreamGEV *>( aStream );

        // Negotiate packet size
        lDeviceGEV->NegotiatePacketSize();

        // Configure device streaming destination
        lDeviceGEV->SetStreamDestination( lStreamGEV->GetLocalIPAddress(), lStreamGEV->GetLocalPort() );
    }
}

void CreateStreamBuffers( PvDevice *aDevice, PvStream *aStream, BufferList *aBufferList )
{
    // Reading payload size from device
    uint32_t lSize = aDevice->GetPayloadSize();

    // Use BUFFER_COUNT or the maximum number of buffers, whichever is smaller
    uint32_t lBufferCount = ( aStream->GetQueuedBufferMaximum() < BUFFER_COUNT ) ? 
        aStream->GetQueuedBufferMaximum() :
        BUFFER_COUNT;

    // Allocate buffers
    for ( uint32_t i = 0; i < lBufferCount; i++ )
    {
        // Create new buffer object
        PvBuffer *lBuffer = new PvBuffer;

        // Have the new buffer object allocate payload memory
        lBuffer->Alloc( static_cast<uint32_t>( lSize ) );
        
        // Add to external list - used to eventually release the buffers
        aBufferList->push_back( lBuffer );
    }
    
    // Queue all buffers in the stream
    BufferList::iterator lIt = aBufferList->begin();
    while ( lIt != aBufferList->end() )
    {
        aStream->QueueBuffer( *lIt );
        lIt++;
    }
}

void AcquireImages( PvDevice *aDevice, PvStream *aStream )
{
    // Get device parameters need to control streaming
    PvGenParameterArray *lDeviceParams = aDevice->GetParameters();

    // Map the GenICam AcquisitionStart and AcquisitionStop commands
    PvGenCommand *lStart = dynamic_cast<PvGenCommand *>( lDeviceParams->Get( "AcquisitionStart" ) );
    PvGenCommand *lStop = dynamic_cast<PvGenCommand *>( lDeviceParams->Get( "AcquisitionStop" ) );

    // Get stream parameters
    PvGenParameterArray *lStreamParams = aStream->GetParameters();

    // Map a few GenICam stream stats counters
    PvGenFloat *lFrameRate = dynamic_cast<PvGenFloat *>( lStreamParams->Get( "AcquisitionRate" ) );
    PvGenFloat *lBandwidth = dynamic_cast<PvGenFloat *>( lStreamParams->Get( "Bandwidth" ) );

    // Enable streaming and send the AcquisitionStart command
    cout << "Enabling streaming and sending AcquisitionStart command." << endl;
    aDevice->StreamEnable();
    lStart->Execute();

    char lDoodle[] = "|\\-|-/";
    int lDoodleIndex = 0;
    double lFrameRateVal = 0.0;
    double lBandwidthVal = 0.0;
    int iters = 0;


    // Makes new directory for images to live in.


                std::ostringstream dateNameStream("");
                //time_t rawtime;
                struct tm * timeinfo;
                char buffer [80];
                struct timeval tv;
                //time (&rawtime);
                //timeinfo = localtime (&rawtime);
                int millisec;
                
                gettimeofday(&tv, NULL);
                timeinfo = localtime(&tv.tv_sec);

                strftime(buffer, 80, "%Y-%m-%d--%H-%M-%S", timeinfo);
                dateNameStream << buffer;

                std::ostringstream dirNameStream("");
                dirNameStream << "/data1/" << dateNameStream.str();
                std::string dirName = dirNameStream.str();

                std::ostringstream commandStream("");
                commandStream << "mkdir -p -m 777 " << dirName;
                std::string command = commandStream.str();
                const int dir_err = system(command.c_str());


    // Acquire images until the user instructs us to stop.
    cout << endl << "<press a key to stop streaming>" << endl;
    while ( !PvKbHit() )
    {
        PvBuffer *lBuffer = NULL;
        PvResult lOperationResult;

        // Retrieve next buffer
        PvResult lResult = aStream->RetrieveBuffer( &lBuffer, &lOperationResult, 1000 );
        if ( lResult.IsOK() )
        {
            if ( lOperationResult.IsOK() )
            {
                PvPayloadType lType;

                //
                // We now have a valid buffer. This is where you would typically process the buffer.
                // -----------------------------------------------------------------------------------------
                // ...

                PvBufferWriter lWriter;


                std::ostringstream imageDateNameStream("");
                gettimeofday(&tv, NULL);
                millisec = lrint(tv.tv_usec/1000.0);
                if (millisec>=1000){
                    millisec -= 1000;
                    tv.tv_sec++;
                }
                // Round up millisecs
                timeinfo = localtime(&tv.tv_sec);
                strftime(buffer, 80, "%Y-%m-%d--%H-%M-%S-", timeinfo);

                imageDateNameStream << buffer << millisec;

                std::ostringstream fileNameStream("");
                fileNameStream << dirName << "/" << imageDateNameStream.str() << ".raw";
                // Need to figure out how to add milliseconds in imageDateNameStream since we
                // have more than one image per second.

                //fileNameStream << dirName << "/image_" << iters << ".raw";
                std::string fileName = fileNameStream.str();
                lWriter.Store( lBuffer, fileName.c_str(),PvBufferFormatRaw );
                iters++;

                lFrameRate->GetValue( lFrameRateVal );
                lBandwidth->GetValue( lBandwidthVal );

                // If the buffer contains an image, display width and height.
                uint32_t lWidth = 0, lHeight = 0;
                lType = lBuffer->GetPayloadType();

                cout << fixed << setprecision( 1 );
                cout << lDoodle[ lDoodleIndex ];
                cout << " BlockID: " << uppercase << hex << setfill( '0' ) << setw( 16 ) << lBuffer->GetBlockID();
                if ( lType == PvPayloadTypeImage )
                {
                    // Get image specific buffer interface.
                    PvImage *lImage = lBuffer->GetImage();

                    // Read width, height.
                    lWidth = lImage->GetWidth();
                    lHeight = lImage->GetHeight();
                    cout << "  W: " << dec << lWidth << " H: " << lHeight;
                }
                else 
                {
                    cout << " (buffer does not contain image)";
                }
                cout << "  " << lFrameRateVal << " FPS  " << ( lBandwidthVal / 1000000.0 ) << " Mb/s   \r";
            }
            else
            {
                // Non OK operational result
                cout << lDoodle[ lDoodleIndex ] << " " << lOperationResult.GetCodeString().GetAscii() << "\r";
            }

            // Re-queue the buffer in the stream object
            aStream->QueueBuffer( lBuffer );
        }
        else
        {
            // Retrieve buffer failure
            cout << lDoodle[ lDoodleIndex ] << " " << lResult.GetCodeString().GetAscii() << "\r";
        }

        ++lDoodleIndex %= 6;
    }

    PvGetChar(); // Flush key buffer for next stop.
    cout << endl << endl;

    // Tell the device to stop sending images.
    cout << "Sending AcquisitionStop command to the device" << endl;
    lStop->Execute();

    // Disable streaming on the device
    cout << "Disable streaming on the controller." << endl;
    aDevice->StreamDisable();

    // Abort all buffers from the stream and dequeue
    cout << "Aborting buffers still in stream" << endl;
    aStream->AbortQueuedBuffers();
    while ( aStream->GetQueuedBufferCount() > 0 )
    {
        PvBuffer *lBuffer = NULL;
        PvResult lOperationResult;

        aStream->RetrieveBuffer( &lBuffer, &lOperationResult );
    }
}

void FreeStreamBuffers( BufferList *aBufferList )
{
    // Go through the buffer list
    BufferList::iterator lIt = aBufferList->begin();
    while ( lIt != aBufferList->end() )
    {
        delete *lIt;
        lIt++;
    }

    // Clear the buffer list 
    aBufferList->clear();
}


