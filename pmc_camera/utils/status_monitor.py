import curses, curses.wrapper
import time
import Pyro4
import Pyro4.errors
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.COMMTIMEOUT = 0.2

important_camera_parameters=[ "AcquisitionFrameCount", "AcquisitionFrameRateAbs", "AcquisitionFrameRateLimit",
                              "AcquisitionMode","ChunkModeActive",
                             "DeviceTemperature", "DeviceTemperatureSelector",  "EFLensFStopCurrent",
                              "EFLensFStopMax", "EFLensFStopMin", "EFLensFStopStepSize",
                             "EFLensFocusCurrent",  "EFLensFocusMax", "EFLensFocusMin", "EFLensFocusSwitch", "EFLensID",
                              "EFLensLastError", "EFLensState",
                             #"EventAcquisitionEndFrameID", "EventAcquisitionEndTimestamp",
                            # "EventAcquisitionRecordTrigger", "EventAcquisitionRecordTriggerFrameID", "EventAcquisitionRecordTriggerTimestamp", "EventAcquisitionStart", "EventAcquisitionStartFrameID", "EventAcquisitionStartTimestamp", "EventAction0", "EventAction0FrameID", "EventAction0Timestamp", "EventAction1", "EventAction1FrameID", "EventAction1Timestamp", "EventError", "EventErrorFrameID", "EventErrorTimestamp", "EventExposureEnd", "EventExposureEndFrameID", "EventExposureEndTimestamp", "EventExposureStart", "EventExposureStartFrameID", "EventExposureStartTimestamp", "EventFrameTrigger", "EventFrameTriggerFrameID", "EventFrameTriggerReady", "EventFrameTriggerReadyFrameID", "EventFrameTriggerReadyTimestamp", "EventFrameTriggerTimestamp", "EventLine1FallingEdge", "EventLine1FallingEdgeFrameID", "EventLine1FallingEdgeTimestamp", "EventLine1RisingEdge", "EventLine1RisingEdgeFrameID", "EventLine1RisingEdgeTimestamp", "EventLine2FallingEdge", "EventLine2FallingEdgeFrameID", "EventLine2FallingEdgeTimestamp", "EventLine2RisingEdge", "EventLine2RisingEdgeFrameID", "EventLine2RisingEdgeTimestamp", "EventNotification", "EventOverflow", "EventOverflowFrameID", "EventOverflowTimestamp", "EventPtpSyncLocked", "EventPtpSyncLockedFrameID", "EventPtpSyncLockedTimestamp", "EventPtpSyncLost", "EventPtpSyncLostFrameID", "EventPtpSyncLostTimestamp", "EventSelector", "EventsEnable1",
                            "ExposureAuto", "ExposureAutoAdjustTol", "ExposureAutoAlg", "ExposureAutoMax", "ExposureAutoMin",
                             "ExposureAutoOutliers", "ExposureAutoRate", "ExposureAutoTarget", "ExposureMode", "ExposureTimeAbs",
                              "Gain", "GainAuto", "GevTimestampValue", "PixelFormat", "PtpAcquisitionGateTime", "PtpMode", "PtpStatus",
                             "StatFrameDelivered", "StatFrameDropped", "StatFrameRate", "StatFrameRescued", "StatFrameShoved",
                             "StatFrameUnderrun", "StatLocalRate", "StatPacketErrors", "StatPacketMissed", "StatPacketReceived",
                             "StatPacketRequested", "StatPacketResent", "StatTimeElapsed",
                             "StreamAnnouncedBufferCount", "StreamBytesPerSecond",
                             "StreamHoldEnable", "StreamID", "StreamType", "TriggerMode", "TriggerSource"]

def display_status(stdscr,proxy):
    # Set non-blocking input
    stdscr.nodelay(1)
    run = 1

    # Look like gbtstatus (why not?)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    keycol = curses.color_pair(1)
    valcol = curses.color_pair(2)
    errcol = curses.color_pair(3)
    status = {}
    new_data = False
    # Loop
    while (run):
        try:
            status = proxy.get_status()
            new_data = True
        except (Pyro4.errors.ConnectionClosedError, Pyro4.errors.CommunicationError,
                Pyro4.errors.TimeoutError):
            new_data=False

        camera_parameters = status.pop('all_camera_parameters',{})
        for key in important_camera_parameters:
            status[key] = camera_parameters.pop(key,'')

        # Reset screen
        stdscr.erase()

        # Draw border
        stdscr.border()

        # Get dimensions
        (ymax,xmax) = stdscr.getmaxyx()

        # Display main status info
        onecol = False # Set True for one-column format
        col = 2
        curline = 0
        if new_data:
            stdscr.addstr(curline,col,"Current status:", keycol)
        else:
            stdscr.addstr(curline,col,"Last status (no connection):", errcol)

        curline += 2
        flip=0
        for k,v in status.items():
            if (curline < ymax-3):
                stdscr.addstr(curline,col,"%27.27s : "%k, keycol)
                value = str(v)[:32]
                stdscr.addstr("%27.27s" % value, valcol)
            else:
                stdscr.addstr(ymax-3,col, "-- Increase window size --", errcol)
            if (flip or onecol):
                curline += 1
                col = 2
                flip = 0
            else:
                col = 60
                flip = 1
        # Bottom info line
        stdscr.addstr(ymax-2,col,"Last update: " + time.asctime() \
                + "  -  Press 'q' to quit")

        # Redraw screen
        stdscr.refresh()

        # Sleep a bit
        time.sleep(.27)

        # Look for input
        c = stdscr.getch()
        while (c != curses.ERR):
            if (c==ord('q')):
                run = 0
            elif (c==ord('n')):
                proxy.close()
            c = stdscr.getch()

if __name__ == "__main__":
    proxy = Pyro4.Proxy('PYRO:pipeline@pmc-camera-1:50000')
    try:
        curses.wrapper(display_status,proxy)
    except KeyboardInterrupt:
        print "Exiting..."