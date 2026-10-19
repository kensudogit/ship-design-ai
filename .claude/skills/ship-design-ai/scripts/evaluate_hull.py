"""教育用の排水容積・排水質量。船級承認・実船排水の鑑定ではない。∇ = Lpp×B×T×Cb。"""
import argparse

DENSITY = 1.025


def evaluate(length: float, beam: float, draft: float, cb: float, density: float = DENSITY) -> dict:
    if min(length, beam, draft, density) <= 0 or not (0 < cb <= 1):
        raise ValueError("寸法と密度は正、Cbは(0,1]で指定してください")
    volume = length * beam * draft * cb
    return {
        "volume_m3": round(volume, 3),
        "displacement_tonnes": round(volume * density, 3),
        "density": density,
        "note": "educational volume. not class-approved",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--length", type=float, required=True)
    p.add_argument("--beam", type=float, required=True)
    p.add_argument("--draft", type=float, required=True)
    p.add_argument("--cb", type=float, required=True)
    a = p.parse_args()
    print(evaluate(a.length, a.beam, a.draft, a.cb))
