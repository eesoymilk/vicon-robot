import pandas as pd

ROBOT_INIT_POSE = (0.410444, 0.080962, 0.547597)
ROBOT_INIT_ROT = (179.99847, -0.000170, 84.27533)


def get_hand_df() -> pd.DataFrame:
    df = pd.read_csv("hand_cal.csv", header=None)

    marker_row = df.iloc[0]
    axis_row = df.iloc[1]
    df = df.iloc[3:].reset_index(drop=True).apply(pd.to_numeric, errors="coerce")

    columns = [(marker, axis) for marker, axis in zip(marker_row, axis_row)]

    multi_index = pd.MultiIndex.from_tuples(columns, names=["Marker", "Axis"])
    df.columns = multi_index

    return df


def get_hand_tracking_coords():
    df = get_hand_df()

    hand_ref_marker = "Hand:Center"

    # delta = (
    #     df[hand_ref_marker]["X"][0] / 1000 - ROBOT_INIT_POSE[0],
    #     df[hand_ref_marker]["Y"][0] / 1000 - ROBOT_INIT_POSE[1],
    #     df[hand_ref_marker]["Z"][0] / 1000 - ROBOT_INIT_POSE[2]
    # )

    for index_row in df[hand_ref_marker].iterrows():
        print(
            f"Delta: ({index_row[1]['X'] - df[hand_ref_marker]['X'][0]}, {index_row[1]['Y'] - df[hand_ref_marker]['Y'][0]}, {index_row[1]['Z'] - df[hand_ref_marker]['Z'][0]})"
        )
        yield (
            (index_row[1]["X"] - df[hand_ref_marker]["X"][0]) / 1000
            + ROBOT_INIT_POSE[0],
            (index_row[1]["Y"] - df[hand_ref_marker]["Y"][0]) / 1000
            + ROBOT_INIT_POSE[1],
            (index_row[1]["Z"] - df[hand_ref_marker]["Z"][0]) / 1000
            + ROBOT_INIT_POSE[2],
        )


def main(): ...


if __name__ == "__main__":
    main()
