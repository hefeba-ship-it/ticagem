import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RomaneioRecord:
    romaneio: str
    col_e: object       # int RQ number or str 'BuscaXXXXXX'
    col_f: str          # = romaneio
    col_g: str          # 'Entrega' or 'Coleta'
    col_j: int = 12
    col_k: str = ''     # last RQ 'NNNNNN - S' or product chars[6:16]
    col_l: str = ''     # customer code (7-char raw field)
    col_m: str = ''     # customer name (trimmed)
    col_o: str = ''     # full address
    col_x: str = ''     # phone


def parse_phone(tel_portion: str) -> str:
    # Fixed-width format after 'TEL': ' DD   NNNNNNNNN   '
    # +1-2: 2-char DDD field, +6-14: 9-char number field (may be 7-9 digits + spaces)
    m = re.search(r'TEL', tel_portion, re.IGNORECASE)
    if not m:
        return ''
    pos = m.end()
    if pos + 15 > len(tel_portion):
        return ''
    ddd = tel_portion[pos + 1:pos + 3].strip()
    num = tel_portion[pos + 6:pos + 15].strip()
    if not ddd or not num:
        return ''
    if len(num) == 8:
        return ddd + '9' + num
    return ddd + num


def parse_txt(content: str) -> list[RomaneioRecord]:
    records = []
    seen = set()

    # Split by separator lines (sequences of Ä chars)
    blocks = re.split(r'Ä{5,}', content)

    for block in blocks:
        lines = block.split('\n')

        # Find the ROMANEIO line
        rom_idx = None
        for i, line in enumerate(lines):
            if re.match(r' ROMANEIO:\d{6}\s', line):
                rom_idx = i
                break
        if rom_idx is None:
            continue

        rom_line = lines[rom_idx]
        if len(rom_line) < 30:
            continue

        romaneio = rom_line[10:16].strip()
        if not romaneio or romaneio in seen:
            continue
        seen.add(romaneio)

        customer_code = rom_line[20:27]           # raw 7 chars (may have trailing space)
        customer_name = rom_line[30:68].strip()   # 38-char fixed-width name field (pos 30-67)
        addr1 = rom_line[70:].rstrip('\r\n')      # address starts at col 70; empty on overflow lines

        # Second line: address continuation + phone
        addr2 = ''
        phone = '9'
        if rom_idx + 1 < len(lines):
            line2 = lines[rom_idx + 1]
            tel_m = re.search(r'(?<!\w)TEL\s', line2, re.IGNORECASE)
            if tel_m:
                tel_pos = tel_m.start()
                addr2 = line2[:tel_pos].rstrip()
                phone = parse_phone(line2[tel_pos:])
            else:
                addr2 = line2.rstrip()

        # Build full address: strip trailing spaces from addr1, join with one space
        a1 = addr1.rstrip()
        full_addr = (a1 + ' ' + addr2) if addr2 else a1

        # Classify block: Entrega (has RQ.: lines) vs Coleta (CODIGO DESCRICAO only)
        rq_lines = [l for l in lines if re.match(r' RQ\.:', l)]
        cod_lines = [l for l in lines if re.match(r' \d{5} ', l)]

        if rq_lines:
            last_rq = rq_lines[-1]
            col_k = last_rq[6:16]                 # '453070 - 6' format
            rq_num_str = col_k.split(' - ')[0].strip()
            col_e = int(rq_num_str) if rq_num_str.isdigit() else rq_num_str
            col_g = 'Entrega'
        elif cod_lines:
            first_cod = cod_lines[0]
            col_k = first_cod[6:16] if len(first_cod) >= 16 else first_cod[6:]
            col_e = 'Busca' + romaneio
            col_g = 'Coleta'
        else:
            continue  # skip blocks without product lines

        records.append(RomaneioRecord(
            romaneio=romaneio,
            col_e=col_e,
            col_f=romaneio,
            col_g=col_g,
            col_j=12,
            col_k=col_k,
            col_l=customer_code,
            col_m=customer_name,
            col_o=full_addr,
            col_x=phone,
        ))

    return records
