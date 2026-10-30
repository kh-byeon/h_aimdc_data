# IGZO 4T2C 어레이 — 거리 연산(L2) 실측 정리

**칩** chip6 / site `dist` · **측정** 2026-09-03 ~ 09-04 · **주 런** `chip6_dist_mbl-1p00_0904_171519`
**데이터셋** `4t2c_distance_paper_20260904.xlsx` (시트별 tidy 자료) · **작도 스크립트** `plot_figures.py`

---

## 1. 한 문장 요약

4×2 IGZO 4T2C 상보 셀 어레이에서, SL 을 차동 인가하는 단일 읽기 동작만으로
질의 벡터와 저장 벡터 사이의 **가중 제곱 유클리드 거리를 모든 row 에 대해 동시에** 얻었다.
1-D 스윕 교정값만으로 2-D 응답을 예측했을 때 **R² = 0.962 (row3), 0.909 (row0)**,
정규화 RMSE 4.4 % / 5.9 % 였고, 최근접 이웃(argmin) 판정 정확도는 **95.8 %** (n = 96, 우연 50 %) 였다.

---

## 2. 동작 원리 (Methods 문단 초안)

각 4T2C 셀은 두 개의 2T1C 반쪽이 하나의 RBL 을 공유하는 상보 구조다.
저장값 `w` 는 인접한 두 column 에 `BL = +w` / `−w` 로 써넣는다.

읽기에서 pair *j* 의 두 SL 에 차동 전압을 인가하면

```
SL_{2j}   = +v + s
SL_{2j+1} = −v + s
```

셀 전류가 **노치(notch)** 라 부르는 최소점을 가지며 그 위치는

```
v0 = − w / α + b
```

로 저장값에 선형 대응한다 (α = 용량 결합비). 노치 근방을 2차로 전개하면

```
I_rj(x_j) ≈ f_rj + κ_rj (x_j − v0_rj)²
```

이고, 한 row 의 셀들은 같은 RBL 로 전류가 합산되므로

```
I_row_r(x) = S_r + Σ_j κ_rj (x_j − v0_rj)²
```

즉 **row 전류 그 자체가 질의 벡터 x 와 저장 벡터 v0_r 사이의 κ-가중 제곱 유클리드 거리**다.
SL 은 column 공유, RBL 은 row 별 분리이므로 한 번의 SL 인가로 N_ROW 개의 거리가 병렬로 나온다.
본 측정에서는 `rbl_inh = 0xD`, `rbl_ctrl = 0xF00` 로 TIA 채널 8–11 을 동시에 연결하고
4-way 병렬 ADC 로 읽었다.

**중첩성 검증 절차 (핵심).** 각 pair 를 1-D 로만 스윕하여 셀별 `v0`, `κ`, row 바닥 `S_r` 을 얻고,
**2-D 데이터에는 단 하나의 파라미터도 맞추지 않은 채** 위 식으로 2-D 응답을 예측했다.
바닥 `S_r` 은 외삽 대신 `x = v0_r` 질의로 직접 측정했다 (`FLOOR_MODE = "direct"`).

---

## 3. 그림 계획

| Fig | 내용 | 시트 | 축 / 시리즈 |
|---|---|---|---|
| **1** | 셀·어레이 모식도 + 동작 원리 | (작도) | 회로도 + `I_row = S + Σκ(x−v0)²` 수식 |
| **2** | 노치 응답 `I(v)` | `Fig2_notch_curves` | x=`v_V`, y=`I_uA`, 시리즈=`w_store_V`, 패널=`cell` |
| **3** | `v_notch` vs `w` 선형성 → α | `Fig3_vnotch_vs_w`, `Fig3b_alpha_fit`, `Fig3c_alpha_percell` | x=`w_store_V`, y=`v_notch_V`, 오차막대=`v_notch_se_V` |
| **4** | 중첩성: 측정 vs 예측 | `Fig4_superposition`, `Fig4b_superposition_stats` | x=`code_pred`, y=`code_meas`, 1:1 선, row 별 패널 |
| **5** | 2-D 거리 맵 / 결정 경계 ★ | `Fig5_distance_map_2D` | `x0`×`x1` 격자 히트맵 + argmin 경계 |
| **6** | argmin 정확도 막대 | `Fig6b_argmin_summary` (+`Fig6_argmin_detail`) | 후보조합 × 기준①②③, 우연선 0.5 |
| **7** | 셀 산포 | `Fig7_cell_cal`, `Fig7b_floor_error` | (a) κ 히스토그램 (b) v0 vs w (c) 바닥 오차 |
| **S1** | WWL 핀 스캔 | `SupB_wwl_pinscan`, `SupB2_wwl_verdict` | 핀 × row 히트맵 (dw) |
| **S2** | 무바이어스 MBL 스윕 | `SupC_mblscan` | x=`mbl_V`, y=`code`, row 별 |
| **S3** | 조건 탐색 | `SupA_condition_scan` | 손잡이별 nrmse |

> **Fig 5 는 아직 비어 있다.** `igzo_4t2c_dist_opt.py` 의 `grid 9` 결과
> (`4t2c_dist_grid_<TAG>.csv`, 열 `i, x0, x1, row, code`) 가 나오면 그 시트에 채우면 된다.
> 헤드라인 그림이므로 반드시 확보할 것.

### 캡션 초안

**Fig 2.** *Notch response of the 4T2C cell.* RBL current versus differential SL amplitude `v`
for stored values `w` = −0.5 … +0.5 V (MBL = −1.5 V). The current minimum shifts monotonically
with `w`, which is the mechanism that maps a stored analog value onto a distance origin.

**Fig 3.** *Linearity of the notch position.* Measured `v_notch` versus stored `w` for eight
cells; error bars are the quadratic-fit standard errors. The best cells (R2C0, R2C1) give
slope −1.753 / −1.756 (R² = 0.994 / 0.997), i.e. α = 0.570. A direct two-point extraction at
`w = ±0.35 V` gives a median α = 0.588 across the die (range 0.502–0.603 excluding the
defective cell R1C1).

**Fig 4.** *Superposition holds: the array computes a sum of per-cell parabolas.* Measured RBL
code versus the code predicted **from 1-D calibration alone**, with no parameter fitted to the
2-D data (n = 96 queries × 3 stored patterns). Solid line is 1:1. Row 3: R² = 0.962,
normalized RMSE 4.4 %; row 0: R² = 0.909, 5.9 %. Row 1 (open symbols) is a defective cell,
see Fig 7c.

**Fig 5.** *Two-dimensional distance map and decision boundary.* RBL current of each row over a
9 × 9 grid of query vectors `(x_0, x_1)`. Each row's response is a bowl centred on its stored
vector; the argmin boundary (dashed) is the hardware-realized nearest-neighbour partition, and
it agrees with the software boundary computed from the calibrated centres.

**Fig 6.** *Nearest-neighbour accuracy.* Fraction of queries for which the hardware argmin
agrees with each software reference: ① κ-weighted distance with calibrated centres,
② unweighted Euclidean with calibrated centres, ③ pure software using the nominal α, b.
n = 96, chance level 0.5 (dashed). Replacing the defective row 1 by its replica row 3 raises
① from 74.0 % to 95.8 %, showing the accuracy limit is a single bad cell rather than the
architecture.

**Fig 7.** *Cell-to-cell variation.* (a) Distribution of the curvature κ over 24 cell-pattern
instances: mean 168 code/V², range 101–313 (3.1× spread). (b) Calibrated centre `v0` versus
stored `w`. (c) Error of the extrapolated row floor `S` against a direct measurement at
`x = v0`; row 1 deviates by +165 / +240 / +343 code in the three patterns while every other row
stays within −24 … −1 code.

---

## 4. 핵심 수치

### 4.1 중첩성 (MBL = −1.0 V, α = 0.588, 패턴 3 × 질의 32 = 96, 236 s)

| row | slope | R² | R²(오프셋) | R²(모양) | RMSE/폭 | 압축 |
|---|---|---|---|---|---|---|
| row0 | 0.864 | 0.909 | 0.916 | 0.939 | 5.9 % | −0.136 |
| row1 ✗ | 0.626 | 0.106 | 0.243 | 0.378 | 23.7 % | −0.374 |
| row2 | 0.755 | 0.808 | 0.833 | 0.931 | 8.7 % | −0.245 |
| row3 | 0.854 | **0.962** | 0.965 | **0.994** | **4.4 %** | −0.146 |

*R²* = 자유 파라미터 0 개(1:1 선), *R²(오프셋)* = 오프셋만 자유, *R²(모양)* = Pearson r².
세 값의 차이가 바닥 오차 / 이득 오차 / 중첩성 붕괴를 분리한다.

### 4.2 argmin 정확도 (n = 96, 우연 50 %)

| 후보 조합 | ① κ-가중 | ② 유클리드 | ③ 순수 SW |
|---|---|---|---|
| row0 vs row1 (실행 조합) | 74.0 % | 80.2 % | 83.3 % |
| **row0 vs row3** | **95.8 %** | 88.5 % | 90.6 % |
| row2 vs row1 | 76.0 % | 82.3 % | 85.4 % |
| **row2 vs row3** | **96.9 %** | 87.5 % | 90.6 % |

row1 을 그 복제쌍 row3 으로 바꾸는 것만으로 ① 이 74.0 → 95.8 % 로 오른다.
**정확도 한계는 아키텍처가 아니라 셀 하나였다.**
row0/row2 와 row1/row3 은 WWL 축퇴 때문에 동일 데이터를 저장한 독립 셀 복제쌍이므로
이 교체는 저장 대비(contrast)를 바꾸지 않는 공정한 비교다.

### 4.3 소자 파라미터

- α (용량 결합비) = **0.588** (셀 8 개 중앙값; 범위 0.502–0.603, 불량 셀 R1C1 = 1.520 제외), b = +0.0076 V
- κ (곡률) = **168 code/V² 평균**, 101–313 (3.1× 산포), n = 24
- 노치 스윙 = 120–650 code, TIA Rf = 27 kΩ (보드의 LM2902B 단; v1.0.0 까지 1 MΩ 으로 잘못 적혀 있었다. 1 code = 1.221 mV = 45.2 nA)
- 읽기 시간 = 질의당 약 955 ms (n_samples = 3), 4 row 동시

### 4.4 MBL 의존성

| | row0 R² | row0 RMSE/폭 |
|---|---|---|
| MBL = −1.5 V | 0.116 | 23.5 % |
| **MBL = −1.0 V** | **0.909** | **5.9 %** |

읽기 바이어스를 얕게 하면 압축이 줄고 중첩성이 회복된다.

---

## 5. 한계 및 남은 일

1. **압축 (compression).** 기울기 0.755–0.864 로 측정 응답이 예측보다 일관되게 완만하다.
   이득 오차이지 모양 오차가 아니다 (R²모양 0.93–0.99). TIA 포화 또는 셀 전류의 고차 비선형이
   후보. 읽기 전압/Rf 를 더 훑어야 정량화된다.
2. **κ 산포 3.1×.** 셀마다 거리 가중치가 다르므로 하드웨어가 계산하는 것은 균등 유클리드가
   아니라 κ-가중 거리다. 이것이 ②(균등) 대비 ①(가중) 이 [0,3] 조합에서 더 잘 맞는 이유다.
   응용 관점에서는 학습 시 κ 를 흡수하거나 쓰기 전 κ 를 균등화해야 한다.
3. **규모.** 현재 2 차원(pair 2 개) × 4 row. 스케일링은 미검증.
4. **WWL 배선 축퇴.** 핀 A0≡A2 → row{0,2}, A1≡A3 → row{1,3}, A4/A5 미결선.
   쓰기는 두 그룹 단위로만 가능하고, A6/A7 은 row 를 범위 밖으로 밀어내므로 사용 금지.
   차기 테이프아웃에서 핀 배정을 확인해야 한다.
5. **간헐적 바닥 전류.** 모든 노드를 0 V 로 두어도 row 당 약 63 µA 가 흘렀다(09-04 오전; Rf = 27 kΩ 기준, v1.0.0 의 1.7 µA 는 1 MΩ 가정 값).
   `dark` 로 읽기단은 깨끗함을, `wr 0` 으로 게이트 무관함을, `mblscan` 으로 MBL 무관함을 확인했다.
   Vds = 0 에서 채널 전류는 불가능하므로 RBL 상의 전류원(IGZO 광전류 또는 ESD/전원 누설)으로
   본다. 14:07 경 자연 소멸했고 포화 채널이 row3 → row2 → 소멸로 옮겨간 점이 소자 손상보다
   환경 요인을 지지한다. 논문에는 측정 환경 차폐 조건으로 기술하는 것이 안전하다.
6. **row1 불량.** 바닥 외삽 오차 +165/+240/+343 code, R²모양 0.378, 복제쌍 row3 과의 순위상관
   −0.454. 본문 수치는 row0-vs-row3(또는 row2-vs-row3) 을 쓰고, row1 은 Fig 7c 에서
   "셀 하나의 불량이 판정 정확도를 21 %p 떨어뜨린다" 는 근거로 제시하는 것이 좋다.

### 다음 측정 우선순위

1. **`grid 9`** — Fig 5 헤드라인 확보. (진행 중)
2. **압축 정량화** — MBL 을 −0.6 … −1.2 V 로 5 점, 각 조건 짝지음(PAIRED) 으로 slope 추이.
3. **N 확대** — pair 4 개(4 차원) 로 늘려 중첩성이 차원에 대해 유지되는지 확인.
4. **재현성** — 동일 패턴 재기록 후 v0 드리프트 측정 (retention 데이터와 결합).

---

## 6. 데이터 출처

| 시트 | 원본 파일 |
|---|---|
| Fig2 | `4t2c_arr_points_chip6_4t2c_array_mbl-1p50_0903_184122.csv` |
| Fig3 / 3b | `4t2c_arr_notch_...0903_184122.csv`, `4t2c_arr_fit_...0903_184122.csv` |
| Fig3c | 세션 로그 `4t2c_arr_report_chip6_4t2c_array_0904_1435.txt` (α 직접 측정) |
| Fig4 / 6 / 7 | `4t2c_dist_points_chip6_dist_mbl-1p00_0904_171519.csv` (+ `_cal_`, `_status_`) |
| Fig4c | `4t2c_dist_points_chip6_dist_mbl-1p50_0904_170233.csv` |
| SupA | `4t2c_opt_chip6_opt_0904_144241.csv`, `..._160249.csv` |
| SupB | `4t2c_arr_wlscan_latest.json` |
| SupC | `4t2c_arr_mblscan_latest.json` |

**주의 (SupA).** 첫 조건 탐색(`scan_1442`) 은 조건마다 RNG 를 재시드하지 않아 조건마다 다른
저장 패턴을 봤다 — 동일 기준조건을 두 번 재면 nrmse 12 % vs 37 % 로 갈렸다.
조건 간 비교에는 `scan_1602` (PAIRED, 시드 20260904) 만 쓸 것.
또한 R² 는 SStot 이 질의 범위에 의존하는데 그 질의 범위 자체가 탐색 손잡이이므로
순위 지표로 부적합하다 — `nrmse = RMSE / 응답폭` 을 쓴다.
