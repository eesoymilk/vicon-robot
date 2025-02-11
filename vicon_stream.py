import sys
import argparse
from __future__ import print_function
from vicon_dssdk import ViconDataStream


def vicon_init():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "host",
        nargs="?",
        help="Host name, in the format of server:port",
        default="localhost:801",
    )
    args = parser.parse_args()

    client = ViconDataStream.Client()

    try:
        client.Connect(args.host)

        # Check the version
        print("Version", client.GetVersion())

        # Check setting the buffer size works
        client.SetBufferSize(1)

        # Enable all the data types
        client.EnableSegmentData()
        client.EnableMarkerData()
        client.EnableUnlabeledMarkerData()
        client.EnableMarkerRayData()
        client.EnableDeviceData()
        client.EnableCentroidData()

        # Report whether the data types have been enabled
        print("Segments", client.IsSegmentDataEnabled())
        print("Markers", client.IsMarkerDataEnabled())
        print("Unlabeled Markers", client.IsUnlabeledMarkerDataEnabled())
        print("Marker Rays", client.IsMarkerRayDataEnabled())
        print("Devices", client.IsDeviceDataEnabled())
        print("Centroids", client.IsCentroidDataEnabled())

        HasFrame = False
        timeout = 50
        while not HasFrame:
            print(".")
            try:
                if client.GetFrame():
                    HasFrame = True
                timeout = timeout - 1
                if timeout < 0:
                    print("Failed to get frame")
                    sys.exit()
            except ViconDataStream.DataStreamException as e:
                client.GetFrame()

        # Try setting the different stream modes
        client.SetStreamMode(ViconDataStream.Client.StreamMode.EClientPull)
        print("Get Frame Pull", client.GetFrame(), client.GetFrameNumber())

        client.SetStreamMode(ViconDataStream.Client.StreamMode.EClientPullPreFetch)
        print("Get Frame PreFetch", client.GetFrame(), client.GetFrameNumber())

        client.SetStreamMode(ViconDataStream.Client.StreamMode.EServerPush)
        print("Get Frame Push", client.GetFrame(), client.GetFrameNumber())

        print("Frame Rate", client.GetFrameRate())

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
        ) = client.GetTimecode()
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

        print("Total Latency", client.GetLatencyTotal())
        print("Latency Samples")
        for sampleName, sampleValue in client.GetLatencySamples().items():
            print(sampleName, sampleValue)

        print("Frame Rates")
        for frameRateName, frameRateValue in client.GetFrameRates().items():
            print(frameRateName, frameRateValue)

        try:
            client.SetApexDeviceFeedback("BogusDevice", True)
        except ViconDataStream.DataStreamException as e:
            print("No Apex Devices connected")

        client.SetAxisMapping(
            ViconDataStream.Client.AxisMapping.EForward,
            ViconDataStream.Client.AxisMapping.ELeft,
            ViconDataStream.Client.AxisMapping.EUp,
        )
        xAxis, yAxis, zAxis = client.GetAxisMapping()
        print("X Axis", xAxis, "Y Axis", yAxis, "Z Axis", zAxis)

        print("Server Orientation", client.GetServerOrientation())

        try:
            client.SetTimingLog("", "")
        except ViconDataStream.DataStreamException as e:
            print("Failed to set timing log")

        try:
            client.ConfigureWireless()
        except ViconDataStream.DataStreamException as e:
            print("Failed to configure wireless", e)

        return client

    except ViconDataStream.DataStreamException as e:
        print("Handled data stream error", e)


def get_vicon_subject_markers(client, subjectName):
    markers = {}
    marker_names = client.GetMarkerNames(subjectName)
    for marker_name, _ in marker_names:
        markers[marker_name] = client.GetMarkerGlobalTranslation(
            subjectName, marker_name
        )

    return markers


def main():
    client = vicon_init()

    while True:
        get_vicon_subject_markers(client)


if __name__ == "__main__":
    main()
