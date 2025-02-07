from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent


def read_session_csv(file_path: Path) -> pd.DataFrame:
    """Read a session CSV file and return a DataFrame with MultiIndex columns.
    The session CSV file is expected to have the following structure:
    - The first two rows are ignored
    - The third row contains the marker names
    - The fourth row contains the axis names

    Args:
        file_path (Path): Path to the session CSV file

    Returns:
        pd.DataFrame: DataFrame with MultiIndex columns
    """
    df_raw = pd.read_csv(file_path, skiprows=2, header=None)
    df_raw = df_raw.drop(columns=[0, 1]).dropna(axis=1, how="all")

    # df_raw now has rows:
    #   0 => the line with the marker names  (originally line 3 in the file)
    #   1 => the line with Frame,SubFrame,X,Y,Z,... (line 4)
    #   2 => the line with units (line 5)
    #   3+ => actual data (line 6+)

    marker_row = df_raw.iloc[0]
    axis_row = df_raw.iloc[1]
    df = df_raw.iloc[3:].reset_index(drop=True).apply(pd.to_numeric, errors="coerce")

    columns = []
    previous_marker = None
    for marker, axis in zip(marker_row, axis_row):
        if pd.isnull(marker):
            marker = previous_marker
        else:
            previous_marker = marker
        columns.append((marker, axis))

    multi_index = pd.MultiIndex.from_tuples(columns, names=["Marker", "Axis"])
    df.columns = multi_index

    return df


def main() -> None:
    df = read_session_csv(SCRIPT_DIR / "session.csv")

    ref_marker = "ArmJoint6:ToEnd2"
    for axis in ("X", "Y", "Z"):
        slice_idx = (slice(None), axis)
        df.loc[:, slice_idx] -= df.loc[:, (ref_marker, axis)].values[:, None]

    # drop last 3 columns (they are not needed)
    df = df.iloc[:, :-9]
    print(df.head())


if __name__ == "__main__":
    main()
