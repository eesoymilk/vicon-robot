import pandas as pd


def get_hand_df() -> pd.DataFrame:
    df = pd.read_csv("hand_cal.csv", header=None)

    marker_row = df.iloc[0]
    axis_row = df.iloc[1]
    df = df.iloc[3:].reset_index(drop=True).apply(pd.to_numeric, errors="coerce")

    columns = [(marker, axis) for marker, axis in zip(marker_row, axis_row)]

    multi_index = pd.MultiIndex.from_tuples(columns, names=["Marker", "Axis"])
    df.columns = multi_index

    return df


def main() -> None:
    df = get_hand_df()

    print(df.head())

    # loop through df["Hand:Index"] and print X, Y, Z values
    for index_row in df["Hand:Index"].iterrows():
        print(index_row[1]["X"], index_row[1]["Y"], index_row[1]["Z"])


if __name__ == "__main__":
    main()
