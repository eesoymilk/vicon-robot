import sys
from vicon_dssdk import ViconDataStream


class ViconClient:
    _instance = None
    _host = "localhost:801"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super("ViconClient", cls).__new__(cls)
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
            print("Version", self.client.GetVersion())

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
            print("Segments", self.client.IsSegmentDataEnabled())
            print("Markers", self.client.IsMarkerDataEnabled())
            print("Unlabeled Markers", self.client.IsUnlabeledMarkerDataEnabled())
            print("Marker Rays", self.client.IsMarkerRayDataEnabled())
            print("Devices", self.client.IsDeviceDataEnabled())
            print("Centroids", self.client.IsCentroidDataEnabled())

            HasFrame = False
            timeout = 50
            while not HasFrame:
                print(".")
                try:
                    if self.client.GetFrame():
                        HasFrame = True
                    timeout = timeout - 1
                    if timeout < 0:
                        print("Failed to get frame")
                        sys.exit()
                except ViconDataStream.DataStreamException as e:
                    self.client.GetFrame()

            # Try setting the different stream modes
            self.client.SetStreamMode(
                ViconDataStream.self.Client.StreamMode.Eself.ClientPull
            )
            print(
                "Get Frame Pull", self.client.GetFrame(), self.client.GetFrameNumber()
            )

            self.client.SetStreamMode(
                ViconDataStream.self.Client.StreamMode.Eself.ClientPullPreFetch
            )
            print(
                "Get Frame PreFetch",
                self.client.GetFrame(),
                self.client.GetFrameNumber(),
            )

            self.client.SetStreamMode(
                ViconDataStream.self.Client.StreamMode.EServerPush
            )
            print(
                "Get Frame Push", self.client.GetFrame(), self.client.GetFrameNumber()
            )

            print("Frame Rate", self.client.GetFrameRate())

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
            print(
                (
                    "Timecode:",
                    hours,
                    "hours",
                    minutes,
                    "minutes",
                    seconds,
                    "seconds",
                    frames,
                    "frames",
                    subframe,
                    "sub frame",
                    fieldFlag,
                    "field flag",
                    standard,
                    "standard",
                    subFramesPerFrame,
                    "sub frames per frame",
                    userBits,
                    "user bits",
                )
            )

            print("Total Latency", self.client.GetLatencyTotal())
            print("Latency Samples")
            for sampleName, sampleValue in self.client.GetLatencySamples().items():
                print(sampleName, sampleValue)

            print("Frame Rates")
            for frameRateName, frameRateValue in self.client.GetFrameRates().items():
                print(frameRateName, frameRateValue)

            try:
                self.client.SetApexDeviceFeedback("BogusDevice", True)
            except ViconDataStream.DataStreamException as e:
                print("No Apex Devices connected")

            self.client.SetAxisMapping(
                ViconDataStream.self.Client.AxisMapping.EForward,
                ViconDataStream.self.Client.AxisMapping.ELeft,
                ViconDataStream.self.Client.AxisMapping.EUp,
            )
            xAxis, yAxis, zAxis = self.client.GetAxisMapping()
            print("X Axis", xAxis, "Y Axis", yAxis, "Z Axis", zAxis)

            print("Server Orientation", self.client.GetServerOrientation())

            try:
                self.client.SetTimingLog("", "")
            except ViconDataStream.DataStreamException as e:
                print("Failed to set timing log")

            try:
                self.client.ConfigureWireless()
            except ViconDataStream.DataStreamException as e:
                print("Failed to configure wireless", e)

        except ViconDataStream.DataStreamException as e:
            print("Handled data stream error", e)

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
