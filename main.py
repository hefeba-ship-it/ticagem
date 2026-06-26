import re
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from vuupt_parser import parse_txt
from builder import load_prev_day, load_prev_day_full, build_xlsx

app = FastAPI(title="Ticagem Processor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def derive_ddmm(filename: str) -> str:
    """Extract ddmm from filename like 'vuupt2505.TXT' → '2505'."""
    m = re.search(r'(\d{4})', filename)
    return m.group(1) if m else 'output'


@app.post("/process")
async def process(
    txt_file: UploadFile = File(...),
    prev_xlsx: UploadFile = File(...),
):
    txt_bytes = await txt_file.read()
    xlsx_bytes = await prev_xlsx.read()

    # Decode TXT (legacy latin-1 encoding)
    try:
        txt_content = txt_bytes.decode('latin-1')
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao decodificar o arquivo TXT.")

    records = parse_txt(txt_content)
    if not records:
        raise HTTPException(status_code=400, detail="Nenhum romaneio encontrado no arquivo TXT.")

    try:
        prev_mapping = load_prev_day(xlsx_bytes)
        prev_full = load_prev_day_full(xlsx_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler o arquivo do dia anterior: {e}")

    result_bytes = build_xlsx(records, prev_mapping, prev_full)

    ddmm = derive_ddmm(txt_file.filename or '')
    filename = f"ticagem{ddmm}_base.xlsx"

    return Response(
        content=result_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Record-Count": str(len(records)),
            "Access-Control-Expose-Headers": "X-Record-Count, Content-Disposition",
        },
    )


app.mount("/", StaticFiles(directory="static", html=True), name="static")
