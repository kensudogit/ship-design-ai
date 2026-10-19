"""制約通過後の幾何探索例。Holtrop でも実船抵抗でもない。最適とは呼ばない。"""
from scipy.optimize import differential_evolution

TARGET_VOLUME = 40000.0
LPP = (150.0, 220.0)
BEAM = (25.0, 38.0)
DRAFT = (8.0, 13.0)
CB = (0.60, 0.85)


def feasible(length: float, beam: float, draft: float, cb: float) -> bool:
    if min(length, beam, draft) <= 0 or not (0 < cb <= 1):
        return False
    if not (LPP[0] <= length <= LPP[1] and BEAM[0] <= beam <= BEAM[1]):
        return False
    if not (DRAFT[0] <= draft <= DRAFT[1] and CB[0] <= cb <= CB[1]):
        return False
    lb = length / beam
    bt = beam / draft
    return 4.0 <= lb <= 9.0 and 2.0 <= bt <= 4.5


def score(x):
    length, beam, draft, cb = x
    if not feasible(length, beam, draft, cb):
        return 1e6
    volume = length * beam * draft * cb
    penalty = 1000 * (max(0.0, TARGET_VOLUME - volume) / TARGET_VOLUME) ** 2
    return (beam / length) * (1 + cb ** 2) + penalty


if __name__ == "__main__":
    result = differential_evolution(score, [LPP, BEAM, DRAFT, CB], seed=42)
    print("Lpp, B, T, Cb:", result.x)
    print("demo score:", result.fun)
    print("volume:", result.x[0] * result.x[1] * result.x[2] * result.x[3])
    print("feasible:", feasible(*result.x))
    print("note: geometric demo. not measured resistance")
