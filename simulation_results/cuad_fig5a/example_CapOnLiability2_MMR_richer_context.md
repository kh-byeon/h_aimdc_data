# 생성 예시 (v2): "Cap On Liability" (라이선스 계약) — 둘 다 핵심답 성공, 보조 맥락은 MMR만 풍부

> **이 예시는 앞선 Cap On Liability 예시(청구기간 논리 오류가 있던 케이스)의 교체본이다.**
> **다른 계약**(Licensor↔Licensee 소프트웨어 라이선스)이며, MMR 답변에 **사실·논리 오류가 없다.**
> 유일한 흠은 헤더 라벨링 부정확 1건으로, §4에 투명하게 기재한다.

## 한 줄 요약

L2와 MMR **둘 다 핵심 답(책임 상한 조항 §13.1)을 동일하게 정확히 인용**한다. 차이는
**Step 2(변호사가 함께 검토할 보조 조항)의 폭**에서 나타난다. MMR은 **자신만 검색한 청크**에서
**파산·지급불능 종료 트리거, 자산양수(change-of-control)·종료 시 의무, 반환·파기·환불 remedy**
같은 서로 다른 축의 리스크를 끌어오는 반면, L2는 그 자리를 **중복된 면책(indemnification)
조항**으로 채워 새 이슈가 없다. 즉 **"검색 다양성 → 풍부한 보조 맥락"** 의 인과가 성립한다.

> **First figure(No-Solicit)와 상보적**
> - No-Solicit: 다양성이 **핵심답 자체**를 구함 (L2 실패)
> - 이 Cap On Liability: 둘 다 핵심답 성공, 다양성이 **보조 맥락의 풍부함**을 더함 (L2도 성공하나 얕음)

---

## 1. Query & Ground Truth

**Query**
> Highlight the parts (if any) of this contract related to **"Cap On Liability"** that should be
> reviewed by a lawyer. Details: Does the contract include a cap on liability upon the breach of a
> party's obligation? This includes time limitation for the counterparty to bring claims or
> **maximum amount for recovery**.

**Ground Truth** (Licensor↔Licensee 소프트웨어 라이선스 계약) — 다음 스팬들로 구성:
> … *[SEP]* **"Licensor's total liability to Licensee under any provision of this Agreement shall be
> limited to the amount actually paid by Licensee to Licensor for the Licensed Product giving rise
> to the liability."** *[SEP]* … Licensee as its sole remedy may … **return all copies of the
> Licensed Products to Licensor** … and **Licensor shall refund to Licensee the amount paid** …
> *[SEP]* **IN NO EVENT SHALL A PARTY … BE LIABLE … FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR
> CONSEQUENTIAL DAMAGES** … *[SEP]* THE REMEDIES SPECIFIED ABOVE SHALL BE THE SOLE AND EXCLUSIVE
> REMEDIES OF LICENSEE …

> **주목**: GT는 책임 상한(§13.1)뿐 아니라 **반환·파기·환불 remedy 스팬**도 포함한다. 아래에서
> 이 remedy 조항의 검색 여부가 결정적 차이가 된다.

---

## 2. 검색 결과 (top-10) — 겹침과 다양성

> **검색 예산은 동일**: L2·MMR **둘 다 정확히 10개 청크를 검색**한다(문서를 빠트린 게 아님).
> 차이는 "받은 10개가 얼마나 다양한가, 그리고 답변이 그중 몇 개를 실제 근거로 쓰는가"에 있다.

| 구분 | 값 |
|---|---|
| L2 검색 청크 / MMR 검색 청크 | 10 / 10 |
| L2 ∩ MMR (공유 청크) | 6 |
| MMR 전용 청크 | 4 |
| L2 전용 청크 | 4 (모두 §9 면책 조항의 중복 변형) |

### MMR만 검색한 청크 (다양성으로 확보 — 종료·remedy 축)

- **MMR C4 — 파산/지급불능 종료 트리거**: *"…of a petition in **bankruptcy** … **makes an
  assignment for the benefit of creditors**, **ceases doing business** or attempts an unauthorized
  assignment …"*
- **MMR C6 — 반환·파기·환불 remedy**: *"…all copies have been **returned to Licensor or … destroyed**
  … and **Licensor shall refund to Licensee the amount paid** …"* → **GT 스팬과 겹침**(아래 §4).
- **MMR C7 — 자산양수(change-of-control) + 종료 시 의무**: *"…**acquisition of substantially all of
  the assets of Licensee**. **Section 14.3 DUTIES UPON TERMINATION** …"*
- **MMR C8 — 형평법상 구제(specific performance)**: covenants 위반 시 equitable relief.

### L2만 검색한 청크 (모두 §9 면책 중복)

- **L2 C4 / C6 / C7 / C9**: 전부 **§9.1–9.3 INDEMNIFICATION** 조항의 변형·연속. → 이미 다룬 면책
  주제를 반복, 새 이슈 없음.

> **다양성의 실체**: L2는 남는 검색 슬롯을 **면책 조항 중복**으로 채운 반면, MMR은 **종료·insolvency·
> remedy**라는 *다른 축*의 조항을 확보했다. 이것이 Step 2의 폭 차이로 직결된다.

---

## 3. 생성 답변 비교

### Step 1 — Core Finding (핵심답: **동점, 둘 다 정확**)

**L2**
> The contract includes a cap on liability … Chunk 5: **"Licensor's total liability to Licensee
> under any provision of this Agreement shall be limited to the amount actually paid by Licensee to
> Licensor for the Licensed Product giving rise to the liability."**

**MMR**
> Yes, the contract includes a cap on liability … Chunk 2: **"Licensor's total liability to Licensee
> under any provision of this Agreement shall be limited to the amount actually paid …"**

→ **동일한 §13.1 조항을 정확히 인용.** 핵심답 품질 차이 없음(청크 번호만 재정렬).

### Step 2 — Legal Context & Potential Risks (보조 맥락: **MMR이 더 넓음**)

| 보조 이슈 | L2 | MMR | 근거 |
|---|:---:|:---:|---|
| 한도 신뢰(reliance)·다제품 합산 | ✅ | — | L2 C1/C2 |
| 면책 절차(notice) | ✅ | ✅(indemnity) | §9.3 |
| **파산·지급불능 종료 트리거** | ❌ | ✅ | **MMR C4** |
| **자산양수(change-of-control)·종료 시 의무(§14.3)** | ❌ | ✅ | **MMR C7** |
| **반환·파기·환불 remedy** | ❌ | ✅ | **MMR C6 (=GT 스팬)** |
| Survival | ❌ | ✅ | MMR C7/C9 |

**L2 Step 2** (요지) — *책임/면책 클러스터 안에만 머묾*
> Chunk 1: reliance on limitation of liability · Chunk 2: claims against multiple Licensed Products
> shall not enlarge the limit · Chunk 9: indemnification procedure requires prompt written notice.
> → 이어지는 "risks"도 hidden conditions/exceptions 같은 **일반론**.

**MMR Step 2** (요지) — *종료·insolvency·remedy로 확장*
> **Termination rights**: Chunks 4 & 7 outline procedures for terminating the agreement, including
> notice periods and **obligations to return or destroy licensed products** · **Fees/payment**:
> Chunk 6 refunds · **Survival**: Chunks 7 & 9 · Indemnity: Chunk 5.

**Step 2에서 실제 활용(번호 인용)한 서로 다른 청크 수: L2 = 3 vs MMR = 6.**

---

## 4. 왜 이것이 "다양성 → 풍부한 맥락"의 정당한 증거인가 (+ 정직한 유의점)

1. **검색 예산도 핵심답도 공정한 동점** — 양쪽 다 10개 검색, 둘 다 §13.1 책임 상한을 정확 인용.
   "L2가 실패해서" 이기는 구도가 아님.
2. **MMR Step 2의 추가 이슈가 전부 MMR 전용 청크에서 유래** — 파산·종료(C4), 자산양수·종료 시
   의무(C7), 반환·환불 remedy(C6)는 **L2 top-10에 아예 없다.** L2는 같은 슬롯을 §9 면책 중복으로
   소비했다. → 폭 차이의 원인이 **생성 우연이 아니라 검색 다양성**이다.
3. **MMR이 GT 스팬을 더 많이 회수** — GT는 "반환·파기·**환불** remedy" 스팬을 포함하는데, 이를 담은
   **MMR C6를 MMR만 검색**했다. 즉 MMR의 다양성은 단지 "넓은" 것이 아니라 **실제 정답 조항의
   일부를 추가로 근거화**한다.

> **정직한 유의점 (라벨링 부정확 1건)**: MMR은 파산/자산양수 항목을 **"Assignment restrictions"라는
> 헤더로 다소 잘못 분류**했다("assignment for the benefit of creditors"라는 원문 표현에 이끌린 것으로
> 보임). 다만 **서술 내용은 원문에 충실하며**("circumstances under which the agreement can be
> terminated"), **바로 다음 줄에서 동일 청크를 "Termination rights"로 올바르게 재분류**한다. 이는
> 앞 케이스의 *치유기간을 청구기한으로 오인한 사실 오류*와 달리, **분류 라벨의 부정확** 수준이다.
> 또한 MMR Step 2에는 저가치 채움 문장 2개("Exclusivity … not explicitly stated",
> "Confidentiality: No explicit references")가 섞여 있어, **실질 신규 가치는 위 3개 종료·remedy
> 항목**임을 밝혀 둔다.

---

## 5. 양자화 강건성 (fp16 / int8 / int4)

세 양자화 모두 검색은 **각 10개**로 동일. 아래는 Step 2에서 **답변이 실제 활용(번호 인용)한
서로 다른 청크 수**:

| Quantization | L2 Step2 활용 청크 수 | MMR Step2 활용 청크 수 |
|---|:---:|:---:|
| fp16 | 5 | **6** |
| int8 | 3 | **6** |
| int4 | 3 | 3 (동률) |

→ **fp16·int8에서 MMR의 보조 맥락이 더 넓다**(특히 int8에서 3 vs 6로 뚜렷). **int4에서는 동률**로,
효과가 저정밀(int4)에서 약해질 수 있음을 정직하게 기재한다. 핵심답은 세 양자화 모두 양쪽이 정확.

---

## 6. 그림/발표용 한 줄 캡션 (초안)

> **"둘 다 책임 상한 조항(§13.1)을 정확히 찾지만, 변호사가 함께 검토해야 할 파산·자산양수 종료
> 트리거와 반환·환불 remedy는 MMR의 다양한 검색만이 표면화한다 — 그중 하나는 정답 조항 자체다."**

---

*Source: `generation_normalized_{fp16,int8,int4}.json` (H_RAG_cuad_v2.4_MMR_deviceModeling), CUAD intra-document RAG. Canonical figures from int8.*
