"""教育用の幾何スコア探索。抵抗推定や船舶設計の妥当性を保証しない。"""
from scipy.optimize import differential_evolution

TARGET_VOLUME = 40000.0

def score(x):
    length, beam, draft, cb = x
    volume = length * beam * draft * cb
    penalty = 1000 * (max(0.0, TARGET_VOLUME - volume) / TARGET_VOLUME) ** 2
    return (beam / length) * (1 + cb ** 2) + penalty

if __name__ == '__main__':
    result = differential_evolution(score, [(150,220),(25,38),(8,13),(0.60,0.85)], seed=42)
    print('Lpp, B, T, Cb:', result.x)
    print('demo score:', result.fun)
    print('volume:', result.x[0]*result.x[1]*result.x[2]*result.x[3])
