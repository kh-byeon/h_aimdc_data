# CUAD "Cap On Liability" (Q-Cap#2) — L2 vs MMR retrieval-stage dump (int8)

Condition: CUAD intra-document RAG, Llama-3-8B-Instruct, **int8**, top-10 retrieval, symmetric prompt. Document: Licensor↔Licensee software license (doc_id=337). Core clause: **§13.1 LIMIT OF LIABILITY**.

**This is the RETRIEVAL-STAGE output (top-10 slots), NOT the generated answer.** The generated answer cites only a subset of these 10 slots.

Cross-list identifier: `Cxxxx` = md5 of the chunk body (first 120 chars). **The same `Cxxxx` appearing in both lists is literally the same chunk** (shared). `doc_id`=337 for all. The raw LUT `chunk_no` is only a per-list rank (1–10), so it is NOT used as a cross-list identifier. Clause tags are derived from the chunk body (authoritative text is the quote itself).

## Overlap summary

| set | count | slots |
|---|---|---|
| Shared (L2 ∩ MMR) | 6 | L2 ranks 1,2,3,5,8,10  ↔  MMR ranks 1,2,5,3,9,10 |
| L2-only | 4 | L2 ranks 4, 6, 7, 9 |
| MMR-only | 4 | MMR ranks 4, 6, 7, 8 |

### Key findings

1. **Core clause §13.1 is shared** — both lists carry the LIMIT OF LIABILITY clause (`C4234` and its continuation `C21F8`). Neither retriever misses the answer; the difference is entirely in the *other* 8 slots.
2. **All 4 L2-only slots are Article 9 INDEMNIFICATION** — §9.1, §9.2 (twice, overlapping windows), §9.3. See verification table below.
3. **Redundancy is even larger than the 4 exclusives** — one **shared** slot (`C8C2D`, L2 rank 3 / MMR rank 5) is *also* §9.1 INDEMNIFICATION. So **L2 devotes 5 of its 10 slots to §9 indemnification** (1 shared + 4 exclusive), whereas **MMR keeps only that 1 shared §9.1** and reallocates the other 4 slots.
4. **The 4 MMR-only slots are distinct termination-side clauses**: insolvency/bankruptcy termination trigger (`C5CE2`), return/destroy/refund remedy (`C1E48`, which **overlaps the ground-truth span**), §14.3 DUTIES UPON TERMINATION incl. change-of-control asset acquisition (`C6B07`), and equitable-relief/specific-performance (`C1BE9`).

**Query:** Highlight the parts (if any) of this contract related to "Cap On Liability" that should be reviewed by a lawyer. Details: Does the contract include a cap on liability upon the breach of a party’s obligation? This includes time limitation for the counterparty to bring claims or maximum amount for recovery.

**Ground truth (spans):** If such error or discrepancy is not resolved within thirty (30) days after Licensee's [SEP] Licensor's total liability to Licensee under any provision of this Agreement shall be limited to the amount actually paid by Licensee to Licensor for the Licensed Product giving rise to the liability. [SEP] written notice to Licensor, then Licensee as its sole remedy may (a) extend the correction period to a date which is agreeable to Licensor and Licensee or (b) return all copies of the Licensed Products to Licensor with a certification by an authorized representative of Licensee that all copies have been returned to Licensor or have been destroyed and that Licensee has not retained any copies thereof and Licensor shall refund to Licensee the amount paid by Licensee to Licensor for such Licensed Products. [SEP] IN NO EVENT SHALL A PARTY TO THIS AGREEMENT BE LIABLE TO THE OTHER PARTY TO THIS AGREEMENT FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR CONSEQUENTIAL DAMAGES RESULTING FROM THE USE, OR INABILITY TO USE, THE LICENSED PRODUCTS OR ARISING OUT OF THIS AGREEMENT, INCLUDING BUT NOT LMTED TO LOSS OF PROFIT OR OTHER MONETARY LOSS, LOSS OR INTERRUPTION OF DATA OR CONTUTER TIME, ALTERATION OR ERRONEOUS TRANSNUSSION OF DATA OR PROGRAM ERRORS, EVEN IF SUCH PARTY IS ADVISED IN ADVANCE OF THE POSSIBILITY OF SUCH DAMAGES. [SEP] THE REMEDIES SPECIFIED ABOVE SHALL BE THE SOLE AND EXCLUSIVE REMEDIES OF LICENSEE REGARDING THE LICENSED PRODUCTS.

---

## L2 top-10 (retrieval order)

**1.** `[SHARED]` `CE45B` — clauses: **consequential-damages waiver (§13.1 cont.)**

> of claims or suits against more than one Licensed Product shall not enlarge or extend the limit. The parties to this Agreement acknowledge that each of them relied upon the inclusion of this limitation in consideration of entering into this Agreement. IN NO EVENT SHALL A PARTY TO THIS AGREEMENT BE LIABLE TO THE OTHER PARTY TO THIS AGREEMENT FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR CONSEQUENTIAL DAMAGES RESULTING FROM THE USE, OR INABILITY TO USE, THE LICENSED PRODUCTS OR ARISING OUT OF THIS AGREEMENT, INCLUDING BUT NOT LMTED TO LOSS OF PROFIT OR OTHER MONETARY LOSS, LOSS OR INTERRUPTION OF DATA OR CONTUTER TIME, ALTERATION OR

**2.** `[SHARED]` `C4234` — clauses: **§13.1, LIMIT OF LIABILITY**

> REGARDING THE SUITABILITY OF THE LICENSED PRODUCTS FOR THE REQUIREMENTS OF ANY REDISTRIBUTOR. OR CUSTOMER CONCERNING CAPACITY, INTERCONNECTIVITY, EXPANDABILITY OR PERFORMANCE. ARTICLE 13 LIABILITY Section 13.1 LIMIT OF LIABILITY. Licensor's total liability to Licensee under any provision of this Agreement shall be limited to the amount actually paid by Licensee to Licensor for the Licensed Product giving rise to the liability. The existence of claims or suits against more than one Licensed Product shall not enlarge or extend the

**3.** `[SHARED]` `C8C2D` — clauses: **§9.1, INDEMNIFICATION**

> 9.1 INDEMNIFICATION OF LICENSOR. Licensee hereby agrees to defend and indemnify Licensor and Licensor's officers, directors, employees, stockholders, agents and representatives 10 against, and agrees to hold them harmless from, any loss, liability, claim, damage or expense (including reasonable legal fees and expenses incurred therein or in enforcing the indemnity), as incurred, for or on account of or arising from or in connection with or otherwise with respect to any breach of any representation, warranty or covenant of Licensee contained in this Agreement or any document delivered in connection

**4.** `[L2-ONLY]` `CA3EA` — clauses: **§9.2, INDEMNIFICATION**

> 9.2 INDEMNIFICATION OF LICENSEE. Licensor hereby agrees to defend and indemnify Licensee and Licensee's officers, directors, employees, stockholders, agents and representatives against, and agrees to hold them harmless from, any loss, liability, claim, damage or expense (including reasonable legal fees and expenses incurred therein or in enforcing the indemnity), as incurred, for or on account of or arising from or in connection with or otherwise with respect to any breach of any representation, warranty or covenant of Licensor contained in this Agreement or any document delivered in connection

**5.** `[SHARED]` `C21F8` — clauses: **§13.1, LIMIT OF LIABILITY**

> 13.1 LIMIT OF LIABILITY. Licensor's total liability to Licensee under any provision of this Agreement shall be limited to the amount actually paid by Licensee to Licensor for the Licensed Product giving rise to the liability. The existence of claims or suits against more than one Licensed Product shall not enlarge or extend the limit. The parties to this Agreement acknowledge that each of them relied upon the inclusion of this limitation in consideration of entering into this

**6.** `[L2-ONLY]` `C7A67` — clauses: **§9.1, INDEMNIFICATION**

> all costs of such registration and the maintenance and enforcement of all such rights and shall notify Licensee from time to time of all successful and unsuccessful registrations. ARTICLE 9 INDEMNIFICATION Section 9.1 INDEMNIFICATION OF LICENSOR. Licensee hereby agrees to defend and indemnify Licensor and Licensor's officers, directors, employees, stockholders, agents and representatives 10 against, and agrees to hold them harmless from, any loss, liability, claim, damage or expense (including reasonable legal fees and expenses incurred therein or in enforcing the indemnity), as incurred, for or on account of or arising from or in connection with or otherwise with respect to any breach

**7.** `[L2-ONLY]` `CFBAC` — clauses: **§9.2, INDEMNIFICATION**

> or on account of or arising from or in connection with or otherwise with respect to any breach of any representation, warranty or covenant of Licensee contained in this Agreement or any document delivered in connection herewith. Section 9.2 INDEMNIFICATION OF LICENSEE. Licensor hereby agrees to defend and indemnify Licensee and Licensee's officers, directors, employees, stockholders, agents and representatives against, and agrees to hold them harmless from, any loss, liability, claim, damage or expense (including reasonable legal fees and expenses incurred therein or in enforcing the indemnity), as incurred, for or on account of or arising from or in connection with or otherwise with respect to any breach

**8.** `[SHARED]` `C7BBE` — clauses: **§12.4, EXCLUSIVE REMEDIES / warranty disclaimer**

> 12.4 EXCLUSIVE REMEDIES. THE REMEDIES SPECIFIED ABOVE SHALL BE THE SOLE AND EXCLUSIVE REMEDIES OF LICENSEE REGARDING THE LICENSED PRODUCTS. LICENSOR SPECIFICALLY DISCLAIMS ANY AND ALL OTHER WARRANTIES OF ANY KIND, EXPRESS, RAPLIED OR STATUTORY, INCLUDING ANY WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. LICENSOR SPECIFICALLY MAKES NO REPRESENTATIONS REGARDING THE SUITABILITY OF THE LICENSED PRODUCTS FOR THE REQUIREMENTS OF ANY REDISTRIBUTOR. OR CUSTOMER CONCERNING CAPACITY, INTERCONNECTIVITY, EXPANDABILITY OR PERFORMANCE. ARTICLE 13

**9.** `[L2-ONLY]` `C56C5` — clauses: **§9.3, INDEMNIFICATION**

> 9.3 INDEMNIFICATION PROCEDURE. Promptly after acquiring knowledge of any loss, action, suit, investigation, proceeding, demand, assessment, audit, judgment or claim against Licensor or Licensee, or as to which Licensor or Licensee may be liable, a party entitled hereunder to be indemnified shall give written notice thereof to the party obligated hereunder to provide indemnification. The indemnifying party at its own expense promptly shall defend, contest or otherwise protect against any damage, loss, deficiency, liability, claim, encumbrance, penalty, cost, expense,

**10.** `[SHARED]` `C8492` — clauses: **consequential-damages waiver (§13.1 cont.), → Art.14 (Term) boundary**

> relied upon the inclusion of this limitation in consideration of entering into this Agreement. IN NO EVENT SHALL A PARTY TO THIS AGREEMENT BE LIABLE TO THE OTHER PARTY TO THIS AGREEMENT FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR CONSEQUENTIAL DAMAGES RESULTING FROM THE USE, OR INABILITY TO USE, THE LICENSED PRODUCTS OR ARISING OUT OF THIS AGREEMENT, INCLUDING BUT NOT LMTED TO LOSS OF PROFIT OR OTHER MONETARY LOSS, LOSS OR INTERRUPTION OF DATA OR CONTUTER TIME, ALTERATION OR ERRONEOUS TRANSNUSSION OF DATA OR PROGRAM ERRORS, EVEN IF SUCH PARTY IS ADVISED IN ADVANCE OF THE POSSIBILITY OF SUCH DAMAGES. 15 ARTICLE 14 TERM AND

---

## MMR top-10 (retrieval order)

**1.** `[L2_Anchor / SHARED]` `CE45B` — clauses: **consequential-damages waiver (§13.1 cont.)**

> of claims or suits against more than one Licensed Product shall not enlarge or extend the limit. The parties to this Agreement acknowledge that each of them relied upon the inclusion of this limitation in consideration of entering into this Agreement. IN NO EVENT SHALL A PARTY TO THIS AGREEMENT BE LIABLE TO THE OTHER PARTY TO THIS AGREEMENT FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR CONSEQUENTIAL DAMAGES RESULTING FROM THE USE, OR INABILITY TO USE, THE LICENSED PRODUCTS OR ARISING OUT OF THIS AGREEMENT, INCLUDING BUT NOT LMTED TO LOSS OF PROFIT OR OTHER MONETARY LOSS, LOSS OR INTERRUPTION OF DATA OR CONTUTER TIME, ALTERATION OR

**2.** `[L2_Anchor / SHARED]` `C4234` — clauses: **§13.1, LIMIT OF LIABILITY**

> REGARDING THE SUITABILITY OF THE LICENSED PRODUCTS FOR THE REQUIREMENTS OF ANY REDISTRIBUTOR. OR CUSTOMER CONCERNING CAPACITY, INTERCONNECTIVITY, EXPANDABILITY OR PERFORMANCE. ARTICLE 13 LIABILITY Section 13.1 LIMIT OF LIABILITY. Licensor's total liability to Licensee under any provision of this Agreement shall be limited to the amount actually paid by Licensee to Licensor for the Licensed Product giving rise to the liability. The existence of claims or suits against more than one Licensed Product shall not enlarge or extend the

**3.** `[L2_Anchor / SHARED]` `C7BBE` — clauses: **§12.4, EXCLUSIVE REMEDIES / warranty disclaimer**

> 12.4 EXCLUSIVE REMEDIES. THE REMEDIES SPECIFIED ABOVE SHALL BE THE SOLE AND EXCLUSIVE REMEDIES OF LICENSEE REGARDING THE LICENSED PRODUCTS. LICENSOR SPECIFICALLY DISCLAIMS ANY AND ALL OTHER WARRANTIES OF ANY KIND, EXPRESS, RAPLIED OR STATUTORY, INCLUDING ANY WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. LICENSOR SPECIFICALLY MAKES NO REPRESENTATIONS REGARDING THE SUITABILITY OF THE LICENSED PRODUCTS FOR THE REQUIREMENTS OF ANY REDISTRIBUTOR. OR CUSTOMER CONCERNING CAPACITY, INTERCONNECTIVITY, EXPANDABILITY OR PERFORMANCE. ARTICLE 13

**4.** `[MMR-ONLY]` `C5CE2` — clauses: **insolvency/bankruptcy termination trigger**

> of a petition in bankruptcy that is not resolved within thirty (30) days, admits in writing its inability to pay its debts, makes an assignment for the benefit of creditors, ceases doing business or attempts an unauthorized assignment of this Agreement; or (2) Immediately upon written notice if the other party to this Agreement performance of any obligation under this Agreement, including failure to promptly pay any amount due hereunder, and fails to cure such default within thirty (30) days after delivery of written notice specifying the default (with any termination as a result of Licensee's failure to pay amounts due under this Agreement resulting in the acceleration

**5.** `[L2_Anchor / SHARED]` `C8C2D` — clauses: **§9.1, INDEMNIFICATION**

> 9.1 INDEMNIFICATION OF LICENSOR. Licensee hereby agrees to defend and indemnify Licensor and Licensor's officers, directors, employees, stockholders, agents and representatives 10 against, and agrees to hold them harmless from, any loss, liability, claim, damage or expense (including reasonable legal fees and expenses incurred therein or in enforcing the indemnity), as incurred, for or on account of or arising from or in connection with or otherwise with respect to any breach of any representation, warranty or covenant of Licensee contained in this Agreement or any document delivered in connection

**6.** `[MMR-ONLY]` `C1E48` — clauses: **return/destroy/refund remedy**

> with a certification by an authorized representative of Licensee that all copies have been returned to Licensor or have been destroyed and that Licensee has not retained any copies thereof and Licensor shall refund to Licensee the amount paid by Licensee to Licensor for such Licensed Products. Licensee shall pay for all services rendered by Licensor in connection with the Licensed Products or Documentation that are not covered or at that time are no longer covered by the warranty described in this

**7.** `[MMR-ONLY]` `C6B07` — clauses: **§14.3, DUTIES UPON TERMINATION, return/destroy/refund remedy**

> of Licensee's issued and outstanding capital stock or the acquisition of substantially all of the assets of Licensee. Section 14.3 DUTIES UPON TERMINATION. Upon the termination or expiration of the term of this Agreement, the parties shall have the following rights and obligations: (a) Within five (5) days of written demand by Licensor to Licensee, Licensee shall return or destroy all copies of the Licensed Products and any materials associated with the Licensed Products in Licensee's possession or control, except that Licensee may retain sufficient copies of the Master Copy of each Licensed Product

**8.** `[MMR-ONLY]` `C1BE9` — clauses: **equitable relief**

> and other remedies at law would be inadequate in the case of any breach of the covenants contained in this Article 10 and each party to this Agreement agrees that the other party to this Agreement shall be entitled to equitable relief, including the remedy of specific performance, without posting of bond or other security, with respect to any breach or attempted breach of such covenants. ARTICLE 11

**9.** `[L2_Anchor / SHARED]` `C21F8` — clauses: **§13.1, LIMIT OF LIABILITY**

> 13.1 LIMIT OF LIABILITY. Licensor's total liability to Licensee under any provision of this Agreement shall be limited to the amount actually paid by Licensee to Licensor for the Licensed Product giving rise to the liability. The existence of claims or suits against more than one Licensed Product shall not enlarge or extend the limit. The parties to this Agreement acknowledge that each of them relied upon the inclusion of this limitation in consideration of entering into this

**10.** `[L2_Anchor / SHARED]` `C8492` — clauses: **consequential-damages waiver (§13.1 cont.), → Art.14 (Term) boundary**

> relied upon the inclusion of this limitation in consideration of entering into this Agreement. IN NO EVENT SHALL A PARTY TO THIS AGREEMENT BE LIABLE TO THE OTHER PARTY TO THIS AGREEMENT FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR CONSEQUENTIAL DAMAGES RESULTING FROM THE USE, OR INABILITY TO USE, THE LICENSED PRODUCTS OR ARISING OUT OF THIS AGREEMENT, INCLUDING BUT NOT LMTED TO LOSS OF PROFIT OR OTHER MONETARY LOSS, LOSS OR INTERRUPTION OF DATA OR CONTUTER TIME, ALTERATION OR ERRONEOUS TRANSNUSSION OF DATA OR PROGRAM ERRORS, EVEN IF SUCH PARTY IS ADVISED IN ADVANCE OF THE POSSIBILITY OF SUCH DAMAGES. 15 ARTICLE 14 TERM AND

---

## Verification: are the 4 L2-only chunks all §9 INDEMNIFICATION? — YES

| L2 rank | Cross-ID | §9 sub-section | Content |
|---|---|---|---|
| 4 | `CA3EA` | §9.2 INDEMNIFICATION OF LICENSEE | Licensor indemnifies Licensee for breach of Licensor rep/warranty/covenant |
| 6 | `C7A67` | §9.1 INDEMNIFICATION OF LICENSOR | Licensee indemnifies Licensor (chunk opens with §8 registration tail, then ARTICLE 9 / §9.1) |
| 7 | `CFBAC` | §9.2 INDEMNIFICATION OF LICENSEE (window overlapping §9.1 tail) | §9.1 tail → §9.2 header; near-duplicate of rank 4 (same §9.2 text) |
| 9 | `C56C5` | §9.3 INDEMNIFICATION PROCEDURE | Indemnification claim procedure: written notice, defense, contest |

Plus the **shared** §9.1 slot `C8C2D` (L2 rank 3 / MMR rank 5). **Total L2 §9 slots = 5; MMR §9 slots = 1.**

→ **Confirmed.** L2 fills 5/10 slots with Article 9 indemnification (with **§9.2 duplicated** at ranks 4 & 7 — overlapping windows over the same clause). MMR's diversity re-ranking keeps one §9.1 and reallocates the other 4 slots to §14.3 termination-duties, the insolvency/bankruptcy trigger, the return/destroy/refund remedy (overlapping the ground-truth span), and equitable relief — clauses a lawyer reviewing a liability cap would want alongside §13.1.