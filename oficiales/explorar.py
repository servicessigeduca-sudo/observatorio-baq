"""Exploración: descarga los archivos de la Policía y muestra sus columnas."""
import io, re, sys, zipfile
import pandas as pd, requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "ObservatorioBAQ/0.1 (+https://github.com/servicessigeduca-sudo/observatorio-baq)"}
pag = requests.get("https://www.policia.gov.co/estadistica-delictiva", headers=UA, timeout=60)
print("pagina", pag.status_code)
links = sorted({a["href"] for a in BeautifulSoup(pag.text, "html.parser").find_all("a", href=True)
                if re.search(r"\.(xlsx|zip|csv)", a["href"], re.I)})
for l in links: print("LINK", l)
reg = [l for l in links if re.search(r"REGISTRO.*2026|2026.*REGISTRO", requests.utils.unquote(l), re.I)]
cuadro = [l for l in links if re.search(r"mes.a.mes|anualizado", requests.utils.unquote(l), re.I)]
for url in reg[:1] + cuadro[:1]:
    url = requests.compat.urljoin(pag.url, url)
    print("\n=== DESCARGA", url)
    r = requests.get(url, headers=UA, timeout=300); print(r.status_code, len(r.content))
    datos = {}
    if url.lower().endswith(".zip"):
        z = zipfile.ZipFile(io.BytesIO(r.content)); print("ZIP", z.namelist()[:20])
        n = z.namelist()[0]; datos[n] = z.read(n)
    else:
        datos[url] = r.content
    for nombre, b in datos.items():
        x = pd.ExcelFile(io.BytesIO(b)); print("HOJAS", x.sheet_names)
        for hoja in x.sheet_names[:3]:
            raw = pd.read_excel(x, hoja, header=None, nrows=15)
            print("--- hoja", hoja); print(raw.to_string(max_colwidth=40))
        df = pd.read_excel(x, x.sheet_names[0], header=None)
        print("FILAS", len(df))
        mask = df.astype(str).apply(lambda c: c.str.contains("BARRANQUILLA", case=False, na=False)).any(axis=1)
        print("FILAS BARRANQUILLA", int(mask.sum())); print(df[mask].head(10).to_string(max_colwidth=40))
