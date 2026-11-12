import io, pandas as pd, requests
UA = {"User-Agent": "ObservatorioBAQ/0.1 (+https://github.com/servicessigeduca-sudo/observatorio-baq)"}
url = "https://www.policia.gov.co/sites/default/files/INFORMACI%C3%93N_DELITOS_A_NIVEL_DE_REGISTRO_A%C3%91O_2026_3.xlsx"
df = pd.read_excel(io.BytesIO(requests.get(url, headers=UA, timeout=300).content), header=11, dtype=str)
print(df.columns.tolist())
a = df[df["CODIGO DANE"].isin(["08001", "08758", "08433", "08296", "08573"])].copy()
a["CANTIDAD"] = a["CANTIDAD"].astype(int)
print("filas area", len(a), "cantidad", a["CANTIDAD"].sum())
pd.set_option("display.width", 250)
print(a.groupby("DELITO")["CANTIDAD"].sum().sort_values(ascending=False).to_string())
print(a.groupby("MUNICIPIO")["CANTIDAD"].sum().to_string())
print(a.groupby("MES")["CANTIDAD"].sum().to_string())
print(a["FECHA ISSO"].min(), a["FECHA ISSO"].max())
print(a.groupby("ARMAS MEDIOS")["CANTIDAD"].sum().sort_values(ascending=False).head(15).to_string())
