import logging
import sys
import time
from vicon_dssdk import ViconDataStream

logger = logging.getLogger(__name__)


class ViconClient:
    _instance = None
    _host = "localhost:801"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ViconClient, cls).__new__(cls)
            cls._instance._client = ViconDataStream.Client()
            cls._instance.initialize()
        return cls._instance

    def __init__(self):
        pass

    @property
    def client(self):
        return self._client

    def initialize(self):
        try:
            self.client.Connect(self._host)

            # Check the version
            logger.infp("Version", self.client.GetVersion())

            # Check setting the buffer size works
            self.client.SetBufferSize(1)

            # Enable all the data types
            self.client.EnableSegmentData()
            self.client.EnableMarkerData()
            self.client.EnableUnlabeledMarkerData()
            self.client.EnableMarkerRayData()
            self.client.EnableDeviceData()
            self.client.EnableCentroidData()

            # Report whether the data types have been enabled
            logger.info(f"Segment Data Enabled: {self.client.IsSegmentDataEnabled()}")
            logger.info(f"Marker Data Enabled: {self.client.IsMarkerDataEnabled()}")
            logger.info(
                f"Unlabeled Marker Data Enabled: {self.client.IsUnlabeledMarkerDataEnabled()}"
            )
            logger.info(
                f"Marker Ray Data Enabled: {self.client.IsMarkerRayDataEnabled()}"
            )
            logger.info(f"Device Data Enabled: {self.client.IsDeviceDataEnabled()}")
            logger.info(f"Centroid Data Enabled: {self.client.IsCentroidDataEnabled()}")

            timeout = 1.0
            start = time.perf_counter()
            while True:
                try:
                    if self.client.GetFrame():
                        break
                    elif time.perf_counter() - start > timeout:
                        logger.error("Failed to get frame")
                        sys.exit()
                except ViconDataStream.DataStreamException:
                    pass

            # Try setting the different stream modes
            self.client.SetStreamMode(ViconDataStream.Client.StreamMode.EClientPull)
            logger.info(
                f"Get Frame Pull {self.client.GetFrame()} {self.client.GetFrameNumber()}"
            )

            self.client.SetStreamMode(
                ViconDataStream.Client.StreamMode.EClientPullPreFetch
            )
            logger.info(
                f"Get Frame PreFetch {self.client.GetFrame()} {self.client.GetFrameNumber()}"
            )

            self.client.SetStreamMode(ViconDataStream.Client.StreamMode.EServerPush)
            logger.info(
                f"Get Frame Push {self.client.GetFrame()} {self.client.GetFrameNumber()}"
            )

            logger.info(f"Frame Rate {self.client.GetFrameRate()}")

            (
                hours,
                minutes,
                seconds,
                frames,
                subframe,
                fieldFlag,
                standard,
                subFramesPerFrame,
                userBits,
            ) = self.client.GetTimecode()
            logger.info(
                f"Timecode: {hours} hours {minutes} minutes {seconds} seconds {frames} frames {subframe} sub frame {fieldFlag} field flag {standard} standard {subFramesPerFrame} sub frames per frame {userBits} user bits"
            )

            logger.info("Latency", self.client.GetLatencyTotal())
            logger.info(f"Latency Samples: {self.client.GetLatencySamples()}")
            logger.info(f"Frame Rate: {self.client.GetFrameRate()}")

            try:
                self.client.SetApexDeviceFeedback("BogusDevice", True)
            except ViconDataStream.DataStreamException:
                logger.warning("No Apex Devices connected")

            self.client.SetAxisMapping(
                ViconDataStream.Client.AxisMapping.EForward,
                ViconDataStream.Client.AxisMapping.ELeft,
                ViconDataStream.Client.AxisMapping.EUp,
            )
            xAxis, yAxis, zAxis = self.client.GetAxisMapping()
            logger.info(f"X Axis: {xAxis} Y Axis: {yAxis} Z Axis: {zAxis}")

            logger.info(f"Server Orientation: {self.client.GetServerOrientation()}")

            try:
                self.client.SetTimingLog("", "")
            except ViconDataStream.DataStreamException as e:
                logger.warning(f"Failed to set timing log: {e}")

            try:
                self.client.ConfigureWireless()
            except ViconDataStream.DataStreamException as e:
                logger.warning(f"Failed to configure wireless: {e}")

        except ViconDataStream.DataStreamException as e:
            logger.warning(f"Handled data stream error: {e}")

    def get_frame(self):
        return self.client.GetFrame()

    def get_vicon_subject_markers(self, subjectName):
        markers = {}
        marker_names = self.client.GetMarkerNames(subjectName)
        for marker_name, _ in marker_names:
            markers[marker_name] = self.client.GetMarkerGlobalTranslation(
                subjectName, marker_name
            )
        return markers
