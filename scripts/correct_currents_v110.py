#!/usr/bin/env python3
"""v1.1.0 correction of the current columns written by the measurement logger.

The logger converted ADC codes to current with constants from its configuration sheet that were
not updated for the measurement board used here (Supplementary Note 4.9 of the paper):

* TIA-mode reads (IGZO 4T2C cell, 2 x 2 array, 4T2C retention map). The logger used
  TIA_RF_OHM = 1 MOhm; the transimpedance resistor on the board is 27 kOhm (LM2902B stage,
  MCP3208 12-bit ADC at 5 V, so 1 code = 1.221 mV = 45.2 nA). The I_A / I_uA columns were
  therefore 1e6 / 27e3 = 37.04 times too small and are rescaled here. ADC codes and output
  voltages are unchanged. The TIA_RF_OHM entry of each `config` sheet is left as the logger
  wrote it, as a record of what the logger assumed.
* Integrator-mode reads (FeFET retention, 2T1C endurance). The logger converted codes with
  INTEG_CAP_F from its configuration sheet (600 pF and 33 nF in these files); the integration
  capacitance of the board could not be verified from the records, so these columns are not
  absolute currents. They are kept but renamed *_nominal, and every analysis uses the ADC codes.

The edit is made on the worksheet XML, so formatting, charts and images in the workbooks are kept.
Run once from the repository root (it refuses to run twice):

    python scripts/correct_currents_v110.py
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

RF_LOGGER, RF_BOARD = 1.0e6, 27.0e3
SCALE = RF_LOGGER / RF_BOARD

TIA = [  # (file, sheet, columns to rescale)
    ("4t2c_array/4t2c_distance_paper_20260904.xlsx", "Fig2_notch_curves", ["I_uA"]),
    ("4t2c_auto_dataset_0903.xlsx", "recheck_curve", ["I_uA"]),
    ("4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx", "CMSCAN_PTS", ["I_uA"]),
    ("igzo_4t2c_retention/4t2c_map_chip6_4t2c_a_mbl-2p50_0902_155745.xlsx", "response", ["I_A", "I_uA"]),
]
INTEG = [  # (file, sheet, columns to rename, sheets to rename)
    ("2t1c_endurance/endurance_20260724_203233.xlsx", "endurance", ["I_A", "I_uA"], []),
    ("FeFET_retention/1100_dac_retention_v2_20260719_171455.xlsx", "sweeps", ["I_A", "I_uA"], ["matrix_I_uA"]),
    ("FeFET_retention/900_dac_retention_v2_20260720_033639.xlsx", "sweeps", ["I_A", "I_uA"], ["matrix_I_uA"]),
]
TEXT = {  # (file) -> [(old, new)] in string cells
    "4t2c_array/4t2c_distance_paper_20260904.xlsx": [
        ("on-chip TIA (Rf = 1 MOhm)", "board TIA (LM2902B, Rf = 27 kOhm; listed as 1 MOhm before v1.1.0)"),
        ("~1.7 uA/row", "~63 uA/row (Rf = 27 kOhm; 1.7 uA under the former 1 MOhm assumption)")],
    "4t2c_auto_dataset_0903.xlsx": [
        ("TIA CH8 (Rf 1 MΩ)", "TIA CH8 (Rf 27 kΩ; listed as 1 MΩ before v1.1.0)"),
        ("(1 code = 1.221 mV = 1.221 nA)", "(1 code = 1.221 mV = 45.2 nA; 1.221 nA before v1.1.0, which assumed Rf = 1 MΩ)")],
}
CSV = [("4t2c_auto_0903_curves.csv", "i_uA")]  # TIA-mode tables written by the same logger
MARK = "v1.1.0-corrected"


def col_of(ref: str) -> str:
    return re.match(r"[A-Z]+", ref).group(0)


def row_of(ref: str) -> int:
    return int(re.search(r"\d+", ref).group(0))


class Book:
    def __init__(self, path: str):
        self.path = path
        with zipfile.ZipFile(path) as z:
            self.infos = z.infolist()
            self.data = {i.filename: z.read(i.filename) for i in self.infos}
        wb = self.text("xl/workbook.xml")
        rels = self.text("xl/_rels/workbook.xml.rels")
        rid2t = dict(re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
        rid2t.update({a: b for b, a in re.findall(r'<Relationship[^>]*Target="([^"]+)"[^>]*Id="([^"]+)"', rels)})
        self.sheets = {}
        for m in re.finditer(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb):
            t = rid2t[m.group(2)].lstrip("/")
            self.sheets[m.group(1)] = t if t.startswith("xl/") else "xl/" + t
        self.sst = None
        if "xl/sharedStrings.xml" in self.data:
            self.sst = re.findall(r"<si>(.*?)</si>", self.text("xl/sharedStrings.xml"), re.S)

    def text(self, name):
        return self.data[name].decode("utf-8")

    def put(self, name, s):
        self.data[name] = s.encode("utf-8")

    def cell_str(self, cell: str) -> str | None:
        if 't="s"' in cell:
            idx = int(re.search(r"<v>(\d+)</v>", cell).group(1))
            return "".join(re.findall(r"<t[^>]*>([^<]*)</t>", self.sst[idx]))
        if 't="inlineStr"' in cell:
            return "".join(re.findall(r"<t[^>]*>([^<]*)</t>", cell))
        return None

    def header(self, sheet: str, names):
        """Return {name: column letter} from the first row that holds all names."""
        xml = self.text(self.sheets[sheet])
        for rm in re.finditer(r"<row [^>]*>(.*?)</row>", xml, re.S):
            found = {}
            for cm in re.finditer(r'<c r="([A-Z]+\d+)"[^>]*?(?:/>|>.*?</c>)', rm.group(0), re.S):
                v = self.cell_str(cm.group(0))
                if v in names:
                    found[v] = (col_of(cm.group(1)), row_of(cm.group(1)), cm.group(0))
            if len(found) == len(names):
                return found
        raise KeyError(f"{self.path}:{sheet}: header {names} not found")

    def scale(self, sheet, names, factor):
        hdr = self.header(sheet, names)
        cols = {c for c, _, _ in hdr.values()}
        hrow = next(iter(hdr.values()))[1]
        xml = self.text(self.sheets[sheet])
        n = 0

        def one(m):
            nonlocal n
            ref, attrs, val = m.group(1), m.group(2), m.group(3)
            if col_of(ref) not in cols or row_of(ref) <= hrow or 't="' in attrs and 't="n"' not in attrs:
                return m.group(0)
            n += 1
            new = float(val) * factor
            return m.group(0).replace(f"<v>{val}</v>", f"<v>{new:.9g}</v>")
        xml = re.sub(r'<c r="([A-Z]+\d+)"([^>]*)><v>([-+0-9.eE]+)</v></c>', one, xml)
        self.put(self.sheets[sheet], xml)
        return n

    def rename_header(self, sheet, names, suffix):
        hdr = self.header(sheet, names)
        xml = self.text(self.sheets[sheet])
        for name, (_, _, cell) in hdr.items():
            if 't="inlineStr"' in cell:
                new = cell.replace(f">{name}</t>", f">{name}{suffix}</t>")
                assert xml.count(cell) == 1
                xml = xml.replace(cell, new)
            else:  # shared string: append a new string so other cells that share it are untouched
                sst = self.text("xl/sharedStrings.xml")
                idx = len(self.sst)
                sst = sst.replace("</sst>", f"<si><t>{name}{suffix}</t></si></sst>")
                sst = re.sub(r'(count|uniqueCount)="(\d+)"', lambda m: f'{m.group(1)}="{int(m.group(2)) + 1}"', sst)
                self.put("xl/sharedStrings.xml", sst)
                self.sst.append(f"<t>{name}{suffix}</t>")
                new = re.sub(r"<v>\d+</v>", f"<v>{idx}</v>", cell)
                xml = xml.replace(cell, new)
        self.put(self.sheets[sheet], xml)

    def rename_sheet(self, old, new):
        wb = self.text("xl/workbook.xml")
        assert wb.count(f'name="{old}"') == 1
        self.put("xl/workbook.xml", wb.replace(f'name="{old}"', f'name="{new}"'))
        if "docProps/app.xml" in self.data:
            self.put("docProps/app.xml", self.text("docProps/app.xml").replace(f">{old}<", f">{new}<"))
        self.sheets[new] = self.sheets.pop(old)

    def replace_text(self, old, new):
        """Replace in string cells; inline strings may store non-ASCII characters as &#NNN; references."""
        esc = lambda t: "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in t)
        hits = 0
        for name in list(self.data):
            if name == "xl/sharedStrings.xml" or (name.startswith("xl/worksheets/") and name.endswith(".xml")):
                s = self.text(name)
                for o, n in ((old, new), (esc(old), esc(new))):
                    k = s.count(o)
                    if k:
                        s = s.replace(o, n); hits += k
                self.put(name, s)
        return hits

    def mark(self):
        core = "docProps/core.xml"
        if core in self.data:
            s = self.text(core)
            if "<dc:description>" in s:
                s = re.sub(r"<dc:description>(.*?)</dc:description>", lambda m: f"<dc:description>{m.group(1)} {MARK}</dc:description>", s)
            else:  # declare the namespace on the element itself; files differ in where they declare dc
                s = s.replace("</cp:coreProperties>",
                              f'<dc:description xmlns:dc="http://purl.org/dc/elements/1.1/">{MARK}</dc:description></cp:coreProperties>')
            self.put(core, s)

    def marked(self):
        core = "docProps/core.xml"
        return core in self.data and MARK in self.text(core)

    def save(self):
        tmp = self.path + ".tmp"
        with zipfile.ZipFile(tmp, "w") as z:
            for i in self.infos:
                z.writestr(i, self.data[i.filename], compress_type=i.compress_type)
        os.replace(tmp, self.path)


def fix_csv(path, col):
    import csv
    import io
    raw = open(path, encoding="utf-8-sig", newline="").read()
    rows = list(csv.reader(io.StringIO(raw)))
    hdr = rows[0]
    j = hdr.index(col)
    hdr[j] = col  # name unchanged; values rescaled
    for r in rows[1:]:
        if r and r[j] not in ("", "nan"):
            r[j] = f"{float(r[j]) * SCALE:.6g}"
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return "\ufeff" + out.getvalue(), len(rows) - 1


def main() -> int:
    files = sorted({f for f, *_ in TIA} | {f for f, *_ in INTEG})
    books = {f: Book(f) for f in files}
    if any(b.marked() for b in books.values()):
        print("already corrected; nothing done.")
        return 1
    log = []
    for f, sheet, cols in TIA:             # all edits in memory first, then save
        b = books[f]
        n = b.scale(sheet, cols, SCALE)
        for old, new in TEXT.get(f, []):
            assert b.replace_text(old, new) >= 1, (f, old)
        log.append(f"{f} [{sheet}] {cols}: {n} cells x {SCALE:.4f}")
    for f, sheet, cols, sheets in INTEG:
        b = books[f]
        b.rename_header(sheet, cols, "_nominal")
        for s in sheets:
            b.rename_sheet(s, s + "_nominal")
        log.append(f"{f} [{sheet}] {cols} -> *_nominal; sheets {sheets} -> *_nominal")
    csvs = []
    for path, col in CSV:
        txt, n = fix_csv(path, col)
        csvs.append((path, txt)); log.append(f"{path} [{col}]: {n} rows x {SCALE:.4f}")
    for b in books.values():
        b.mark(); b.save()
    for path, txt in csvs:
        open(path, "w", encoding="utf-8", newline="").write(txt)
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
