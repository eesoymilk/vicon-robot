from pathlib import Path
from ..trial.extract import read_trial_csv

SCRIPT_DIR = Path(__file__).resolve().parent

df = read_trial_csv(SCRIPT_DIR / "origin_data.csv")


def get_aubo_coords() -> None:
    base_x = (
        df["Base:XYPlane1"]["X"][0]
        + df["Base:XYPlane2"]["X"][0]
        + df["Base:XYPlane3"]["X"][0]
        + df["Base:XYPlane4"]["X"][0]
    ) / 4
    base_y = (
        df["Base:XYPlane1"]["Y"][0]
        + df["Base:XYPlane2"]["Y"][0]
        + df["Base:XYPlane3"]["Y"][0]
        + df["Base:XYPlane4"]["Y"][0]
    ) / 4
    base_z = df["Base:Zbase"]["Z"][0]

    return base_x, base_y, base_z


def get_origin_coords() -> None:
    origin_x = df["OriginTest:X"]["X"][0]
    origin_y = df["OriginTest:X"]["Y"][0]
    origin_z = df["OriginTest:X"]["Z"][0]

    print(f"Origin: ({origin_x}, {origin_y}, {origin_z})")
