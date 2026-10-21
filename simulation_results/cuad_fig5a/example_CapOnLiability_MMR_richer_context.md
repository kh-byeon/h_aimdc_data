# 생성 예시: "Cap On Liability" — 둘 다 핵심답 성공, 보조 맥락은 MMR만 풍부

## 이 예시를 고른 이유 (한 줄 요약)

L2와 MMR **둘 다 핵심 답(책임 제한 조항)을 동일하게 정확히 인용**한다. 차이는
**Step 2(변호사가 검토할 보조 조항)의 폭**에서 나타난다. MMR은 자신만 검색한
청크에서 **종료권·통지기간·인력배치** 같은 서로 다른 성격의 리스크를 추가로
짚는 반면, L2는 책임/면책 클러스터 안에만 머문다. 즉 **"검색 다양성 → 풍부한
보조 맥락"** 의 인과가 성립하는 케이스다.

> **First figure(No-Solicit)와 상보적**
> - No-Solicit: 다양성이 **핵심답 자체**를 구함 (L2 실패)
> - Cap On Liability: 둘 다 핵심답 성공, 다양성이 **보조 맥락의 풍부함**을 더함 (L2도 성공하나 얕음)
>
> 두 예시로 "다양성이 두 층위(핵심답 + 보조맥락) 모두에서 가치를 준다"를 보인다.

---

## 1. Query & Ground Truth

**Query**
> Highlight the parts (if any) of this contract related to **"Cap On Liability"** that should be
> reviewed by a lawyer. Details: Does the contract include a cap on liability upon the breach of a
> party's obligation? This includes **time limitation for the counterparty to bring claims** or
> **maximum amount for recovery**.

**Ground Truth** (PC Financial ↔ Mobimagic 서비스 계약)
> Neither Party shall be liable to the other Party in contract, tort or otherwise … for any loss of
> profit, business or goodwill or any indirect, incidental or consequential costs … *[SEP]* IN NO
> EVENT WILL EITHER PARTY BE LIABLE FOR ANY CONSEQUENTIAL, INDIRECT, EXEMPLARY, SPECIAL, OR
> INCIDENTAL DAMAGES … NEITHER PARTIES' TOTAL CUMULATIVE LIABILITY … WILL NOT EXCEED THE AGGREGATE
> AMOUNT OF FEES AND EXPENSES OWED BY PC FINANCIAL TO MOBIMAGIC …

> **주목**: 쿼리는 책임 상한액뿐 아니라 **"청구 제기 기간(time limitation to bring claims)"**
> 도 명시적으로 묻는다. 이 하위질문은 아래에서 결정적 차별점이 된다.

---

## 2. 검색 결과 (top-10) — 겹침과 다양성

> **검색 예산은 동일**: L2·MMR **둘 다 정확히 10개 청크를 검색**한다(문서를 빠트린 게 아님).
> 차이는 "몇 개를 받았는가"가 아니라 **"받은 10개가 얼마나 다양한가, 그리고 답변이 그중 몇
> 개를 실제 근거로 활용하는가"** 에 있다.

| 구분 | 값 |
|---|---|
| L2 검색 청크 / MMR 검색 청크 | 10 / 10 |
| L2 ∩ MMR (공유 청크) | 7 |
| MMR 전용 청크 | 3 |
| L2 전용 청크 | 2 (책임/면책 조항의 중복 변형) |

핵심 책임 조항(IN NO EVENT…, TOTAL CUMULATIVE LIABILITY…)은 **양쪽 모두** 상위에
검색했다 → 핵심답은 공정하게 동점. 차이는 **MMR 전용 3개 청크**에 있다.

### MMR만 검색한 청크 (다양성으로 확보)

- **MMR C3 — 종료권(material breach)**: *"This Agreement may be terminated by either Party … if
  the other Party is in material breach … and such breach is not remedied for a period of
  **thirty (30) days** after … notified."*
- **MMR C5 — 인력 배치/배정**: *"Mobimagic may assign its employees to India for short durations …
  less than 183 days in the aggregate in any 12 months."*
- **MMR C9 — 자동 종료 + 통지기간**: *"… for a period of **thirty (30) days** after the Party in
  breach has been notified … This Agreement terminates automatically … if (a) required by
  applicable law; or (b) a receiver [appointed] / bankruptcy …"*

### L2만 검색한 청크

- **L2 C7 / C10**: 둘 다 **책임 제한 조항의 중복 변형** (Neither Party shall be liable… / Mobimagic
  shall not be liable for unforeseen contingency…). → 이미 답한 주제를 반복, 새 이슈 없음.

> **다양성의 실체**: MMR은 같은 책임 조항을 반복 검색하는 대신, **종료·통지·인력배치**라는
> *서로 다른 축*의 조항을 확보했다. 이것이 Step 2의 폭 차이로 직결된다.

---

## 3. 생성 답변 비교

### Step 1 — Core Finding (핵심답: **동점, 둘 다 정확**)

**L2**
> The contract includes a cap on liability … Chunk 2: "IN NO EVENT WILL EITHER PARTY BE LIABLE FOR
> ANY CONSEQUENTIAL, INDIRECT, EXEMPLARY, SPECIAL, OR INCIDENTAL DAMAGES …" Additionally, Chunk 9:
> "NEITHER PARTIES' TOTAL CUMULATIVE LIABILITY … WILL NOT EXCEED THE AGGREGATE AMOUNT OF FEES AND
> EXPENSES OWED BY PC FINANCIAL TO MOBIMAGIC …"

**MMR**
> The contract includes a cap on liability … Chunk 2: "IN NO EVENT WILL EITHER PARTY BE LIABLE …"
> Additionally, Chunk 8: "NEITHER PARTIES' TOTAL CUMULATIVE LIABILITY … WILL NOT EXCEED THE
> AGGREGATE AMOUNT OF FEES AND EXPENSES OWED BY PC FINANCIAL TO MOBIMAGIC …"

→ **동일한 두 조항을 정확히 인용.** 핵심답 품질에 차이 없음. (청크 번호만 재정렬)

### Step 2 — Legal Context & Potential Risks (보조 맥락: **MMR이 더 넓고 정확**)

| 이슈 | L2 | MMR |
|---|:---:|:---:|
| Limitation of liability / fees | ✅ | ✅ |
| Indemnification | ✅ | ✅ |
| Survival clause | ✅ (기간 불명) | ✅ **("5년" 명시)** |
| Confidentiality | ✅ | ✅ |
| **Termination rights (자동 종료·receiver·bankruptcy)** | ❌ | ✅ (C9) |
| **Time limitation for claims (30일 통지기간)** | ❌ | ✅ (C9) |
| **Assignment / 인력배치** | ❌ | ✅ (C3/C5) |
| Step 2에서 실제 활용(번호 인용)한 청크 수 | **3** | **6** |
| 답변 전체에서 실제 활용한 청크 수 (10개 중) | **4** (C1,2,7,9) | **7** (C1,2,3,4,6,8,9) |

**L2 Step 2** (요지)
> indemnification (C4,6,8) · limitation of liability (C2,9,10) · survival (C7,9, *"but do not
> specify which ones"*) · confidentiality · fees/payment · termination (*"but does not specify the
> notice period"*)

→ 대부분 **책임/면책 주변**에 머물고, 종료 통지기간은 *"명시 안 됨"* 으로 마감.

**MMR Step 2** (요지)
> assignment restrictions (C3) · **termination rights** — automatic termination, receiver,
> bankruptcy (C9) · survival — **"survive … for a period of five (5) years"** (C4) · fees/payment
> (C8) · indemnification (C4,C6) · confidentiality (C1) · **time limitation for claims — "30-day
> notice period for breach"** (C9)

→ **쿼리가 명시적으로 물은 "청구 제기 기간"** 하위질문을, MMR만 실제 조항(30일 통지)으로 답한다.
L2는 종료 청크를 검색하지 못해 이 하위질문을 다루지 못한다.

---

## 4. 왜 이것이 "다양성 → 풍부한 맥락"의 정당한 증거인가

1. **검색 예산도 핵심답도 공정한 동점** — 양쪽 다 **10개 청크를 검색**하고, 둘 다 책임 상한 조항을
   정확 인용. "L2가 문서를 덜 받아서" 또는 "L2가 실패해서" 이기는 구도가 아님. 같은 10개를 주고도
   L2는 그중 4개만, MMR은 7개를 실제 근거로 활용한다(활용도 4 vs 7).
2. **MMR Step 2의 추가 이슈가 MMR 전용 청크에서 유래** — 종료권/통지기간(C3,C9), 인력배치(C5)는
   L2 top-10에 아예 없다. 즉 폭 차이의 원인이 **생성 우연이 아니라 검색 다양성**이다.
   (대조: Change Of Control 케이스는 L2도 관련 청크를 갖고도 생성에서 못 써, 다양성이 아닌
   생성 품질 차이였음 → 그래서 이 예시가 더 적절함.)
3. **쿼리 요구사항 커버리지** — 쿼리의 두 번째 하위질문(청구 제기 기간)을 MMR만 충족.
   변호사 관점에서 실질적 가치 차이.

---

## 5. 양자화 강건성 (fp16 / int8 / int4)

세 양자화 모두 검색은 **각 10개**로 동일하다. 아래는 Step 2에서 **답변이 실제로 활용(번호 인용)한
서로 다른 청크 수**의 비교:

| Quantization | L2 Step2 활용 청크 | MMR Step2 활용 청크 |
|---|---|---|
| fp16 | 2 (C1, C9) | **3** (C1, C3, C9) |
| int8 | 3 (C1, C7, C9) | **6** (C1, C3, C4, C6, C8, C9) |
| int4 | 4 (C1, C2, C7, C9) | **5** (C1, C4, C6, C8, C9) |

→ **세 양자화 모두 MMR의 보조 맥락 폭 ≥ L2.** 특히 종료/통지 청크(C3 계열)는 fp16·int8에서
MMR에만 등장. 관찰된 효과가 특정 양자화의 산물이 아님을 보인다.

---

## 6. 그림/발표용 한 줄 캡션 (초안)

> **"둘 다 책임 상한 조항을 정확히 찾지만(핵심답 동점), 변호사가 함께 검토해야 할 종료권·청구
> 제기 기간·인력배치 리스크는 MMR의 다양한 검색만이 표면화한다."**

---

*Source: `generation_normalized_{fp16,int8,int4}.json` (H_RAG_cuad_v2.4_MMR_deviceModeling), CUAD intra-document RAG.*
