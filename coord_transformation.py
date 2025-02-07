from pathlib import Path

from utils.coordinate.origin import get_aubo_coords
from utils.trial.extract import read_trial_csv

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> None:
    df = read_trial_csv(SCRIPT_DIR / "utils" / "trial" / "trial.csv")
    aubo_coords = get_aubo_coords()

    for i, axis in enumerate(("X", "Y", "Z")):
        slice_idx = (slice(None), axis)
        df.loc[:, slice_idx] -= aubo_coords[i]

    # drop last 3 columns (they are not needed)
    df = df.iloc[:, :-9]
    print(df.head())
    df.to_csv(SCRIPT_DIR / "aubo_cal.csv", index=False)


if __name__ == "__main__":
    main()
