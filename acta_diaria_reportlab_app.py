from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
from html import escape
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepInFrame, Paragraph, SimpleDocTemplate, Spacer

APP_DIR = Path(__file__).resolve().parent
MIS_DATOS_PATH = APP_DIR / "acta_diaria_mis_datos.json"
ANIO_LEGAL = 2026

U = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciseis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidos", "veintitres",
    "veinticuatro", "veinticinco", "veintiseis", "veintisiete", "veintiocho", "veintinueve",
]
DEC = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
CEN = {2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def dos(n: int) -> str:
    if n < 30:
        return U[n]
    t, u = divmod(n, 10)
    return DEC[t] + (f" y {U[u]}" if u else "")


def tres(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cien"
    if n < 100:
        return dos(n)
    c, r = divmod(n, 100)
    base = "ciento" if c == 1 else CEN[c]
    return base + (f" {dos(r)}" if r else "")


def apocopar(texto: str) -> str:
    if texto.endswith("veintiuno"):
        return texto[:-9] + "veintiun"
    if texto.endswith("uno"):
        return texto[:-3] + "un"
    return texto


def cardinal(n: int | str) -> str:
    n = int(abs(int(n or 0)))
    if n == 0:
        return "cero"
    mill, resto = divmod(n, 1_000_000)
    miles, cien = divmod(resto, 1000)
    partes: list[str] = []
    if mill:
        partes.append("un millon" if mill == 1 else f"{apocopar(cardinal(mill))} millones")
    if miles:
        partes.append("mil" if miles == 1 else f"{apocopar(tres(miles))} mil")
    if cien:
        partes.append(tres(cien))
    return " ".join(partes)


def num_letras(n: int | str) -> str:
    return cardinal(n)


def num_letras_fem(n: int | str) -> str:
    texto = cardinal(n).replace("cientos", "cientas").replace("quinientos", "quinientas")
    if texto.endswith("uno"):
        texto = texto[:-3] + "una"
    return texto


def num_letras_masc(n: int | str) -> str:
    texto = cardinal(n)
    if texto == "uno":
        return "un"
    if texto.endswith("y uno"):
        return texto[:-3] + "un"
    return texto


def num_letras_envio(valor: str) -> str:
    s = str(valor or "").strip()
    if not s:
        return "cero"
    sin = re.sub(r"^0+", "", s)
    n_ceros = len(s) - len(sin)
    ceros = " ".join(["cero"] * n_ceros)
    if not sin:
        return " ".join(["cero"] * len(s))
    resto = num_letras(int(sin))
    return f"{ceros} {resto}".strip() if ceros else resto


def capitalizar(texto: str) -> str:
    if not texto:
        return ""
    excepciones = {"de", "la", "el", "los", "las", "y", "en", "del", "a"}
    palabras = str(texto).lower().split()
    salida = [p.capitalize() if i == 0 or p not in excepciones else p for i, p in enumerate(palabras)]
    return " ".join(salida).replace("S.a.", "S.A.")


def formatear_cui_legal(cui: str) -> str:
    c = re.sub(r"\D", "", str(cui or "").split(".")[0]).zfill(13)[:13]
    bloques = [c[:4], c[4:9], c[9:]]

    def bloque(valor: str) -> str:
        sin = re.sub(r"^0+", "", valor)
        n_ceros = len(valor) - len(sin)
        ceros = " ".join(["cero"] * n_ceros)
        resto = sin or "0"
        return f"{ceros} {num_letras(int(resto))}".strip()

    return f"{bloque(bloques[0])} espacio {bloque(bloques[1])} espacio {bloque(bloques[2])} ({bloques[0]} {bloques[1]} {bloques[2]})"


def parse_hora(valor: str) -> tuple[int, int]:
    try:
        h, m = str(valor or "0:0").split(":", 1)
        return int(h or 0), int(m or 0)
    except ValueError:
        return 0, 0


def dos_digitos(n: int) -> str:
    return str(n).zfill(2)


def fecha_guatemala() -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Guatemala"))
    except Exception:
        return dt.datetime.now()


def generar_runs(datos: dict, form: dict, ahora: dt.datetime | None = None) -> list[tuple[str, bool]]:
    ahora = ahora or fecha_guatemala()
    runs: list[tuple[str, bool]] = []

    def b(texto: str) -> None:
        runs.append((texto, True))

    def n(texto: str) -> None:
        runs.append((texto, False))

    encargado = str(datos.get("nombre") or "").upper().strip() or "NO REGISTRADO"
    cui = formatear_cui_legal(datos.get("dpi", ""))
    mun = capitalizar(datos.get("municipio", ""))
    dep = capitalizar(datos.get("departamento", ""))
    comedor = capitalizar(datos.get("comedor", ""))
    empresa = capitalizar(form.get("empresa", ""))
    cargo = capitalizar(datos.get("cargo") or "Encargado")
    modal = capitalizar(datos.get("modalidad") or "Fijo")
    direccion = capitalizar(datos.get("direccion") or "Direccion no registrada")

    dia_l = num_letras(ahora.day)
    mes_n = MESES[ahora.month - 1]
    hora_l = num_letras_fem(ahora.hour)
    min_l = num_letras_masc(ahora.minute)
    lbl_h = "hora" if ahora.hour == 1 else "horas"
    lbl_m = "minuto" if ahora.minute == 1 else "minutos"
    art_h = "la" if ahora.hour == 1 else "las"
    no_acta = str(form.get("no_acta") or "0")

    h_des, m_des = parse_hora(form.get("hora_des", ""))
    h_alm, m_alm = parse_hora(form.get("hora_alm", ""))
    art_des = "la" if h_des == 1 else "las"
    art_alm = "la" if h_alm == 1 else "las"
    lbl_hd = "hora" if h_des == 1 else "horas"
    lbl_ha = "hora" if h_alm == 1 else "horas"
    lbl_md = "minuto" if m_des == 1 else "minutos"
    lbl_ma = "minuto" if m_alm == 1 else "minutos"

    r_des = str(form.get("raciones_des") or "0")
    r_alm = str(form.get("raciones_alm") or "0")
    total = int(r_des or 0) + int(r_alm or 0)
    sicome = str(form.get("sicome") or "0")
    sistema = form.get("sistema") or "Sistema de Comedores -SICOME-"
    envd = str(form.get("envio_des") or "0")
    enva = str(form.get("envio_alm") or "0")
    tdi = str(form.get("ticket_des_ini") or "0")
    tdf = str(form.get("ticket_des_fin") or "0")
    tai = str(form.get("ticket_alm_ini") or "0")
    taf = str(form.get("ticket_alm_fin") or "0")
    serie_d = str(form.get("serie_des") or "").upper()
    serie_a = str(form.get("serie_alm") or "").upper()
    incump = form.get("incumplimiento") or "NO"
    horario = form.get("horario") or "SI"
    enterado = "enterada" if cargo.lower() == "encargada" else "enterado"

    b(f"ACTA NUMERO {num_letras(no_acta).upper()} GUION DOS MIL VEINTISEIS ({no_acta}-{ANIO_LEGAL}).")
    n(f" En el municipio de {mun}, departamento de {dep}, siendo {art_h} {hora_l} {lbl_h} con {min_l} {lbl_m} ({dos_digitos(ahora.hour)}:{dos_digitos(ahora.minute)}) del dia {dia_l} ({ahora.day}) de {mes_n} del ano dos mil veintiseis ({ANIO_LEGAL}), constituido en las instalaciones del Comedor Social {modal} {comedor}, ubicado en la {direccion}, del municipio de {mun}, departamento de {dep}; yo, ")
    b(encargado)
    n(f", me identifico con Documento Personal de Identificacion (DPI) con Codigo Unico de Identificacion (CUI) numero {cui}, emitido por el Registro Nacional de las Personas de la Republica de Guatemala, y actuo en mi calidad de ")
    b(f"{cargo} de Comedores")
    n(" de la Subdireccion de Comedores adscrita a la Direccion de Prevencion Social del Viceministerio de Prevencion Social del Ministerio de Desarrollo Social, con el objeto de suscribir la presente Acta para hacer constar lo siguiente: ")
    b("PRIMERO:")
    n(f" En cumplimiento a lo que establece el Manual Operativo del Programa Social \"Comedor Social\" vigente, se procede a realizar el Cierre Administrativo Diario del Comedor Social, mediante la suscripcion de la presente acta, dejando constancia que se realizo el conteo de las raciones de alimentos recibidas de la siguiente forma: a) Que las raciones de desayuno se recibieron a {art_des} {num_letras_fem(h_des)} {lbl_hd} con {num_letras_masc(m_des)} {lbl_md} ({dos_digitos(h_des)}:{dos_digitos(m_des)}); y, b) Que las raciones de almuerzo se recibieron a {art_alm} {num_letras_fem(h_alm)} {lbl_ha} con {num_letras_masc(m_alm)} {lbl_ma} ({dos_digitos(h_alm)}:{dos_digitos(m_alm)}). Se deja constancia que en cada tiempo de comida se verifico el cumplimiento de las caracteristicas organolepticas, asi como, las medidas y/o peso de los alimentos, habiendose realizado la respectiva prueba sensorial. ")
    b("SEGUNDO:")
    n(f" Se verifico el numero de Envio y de tickets electronicos que respaldan la entrega de las raciones de alimentos, por lo que, se deja constancia que: a) En el tiempo de comida de desayuno: se entregaron {num_letras_fem(r_des)} ({r_des}) raciones de alimentos segun Envio de la presente fecha, con serie {serie_d} numero {num_letras_envio(envd)} ({envd}) de ")
    b(empresa)
    n(f"; el rango de los tickets utilizados en este servicio fue del {num_letras_envio(tdi)} al {num_letras_envio(tdf)} ({tdi} al {tdf}); b) En el tiempo de comida de almuerzo: se entregaron {num_letras_fem(r_alm)} ({r_alm}) raciones de alimentos segun Envio de la presente fecha, serie {serie_a} numero {num_letras_envio(enva)} ({enva}) de ")
    b(empresa)
    n(f"; el rango de los tickets utilizados en este servicio fue del {num_letras_envio(tai)} al {num_letras_envio(taf)} ({tai} al {taf}). Por lo que, se hace constar que efectivamente se entregaron el dia de hoy un total de {num_letras_fem(total)} ({total}) raciones de alimentos a la poblacion objetivo y grupos de especial atencion en el Comedor Social de merito. ")
    b("TERCERO:")
    n(f" Al cierre del servicio de alimentacion, se hace constar que {num_letras_fem(sicome)} ({sicome}) personas usuarias fueron registradas en el {sistema}")
    if form.get("sw_hojas"):
        hojas = str(form.get("hojas") or "0")
        n(f", y {num_letras_fem(hojas)} ({hojas}) registradas mediante el uso de las Hojas de Registro de Usuarios e ingresadas al sistema. ")
    else:
        n(". ")
    b("CUARTO:")
    if incump == "SI":
        n(" Se deja constancia que SI hubo incumplimiento en la entrega de raciones de alimentos por parte de la empresa proveedora, adjuntando el informe correspondiente en el que se detalla lo ocurrido, ")
    else:
        n(" Se deja constancia que NO hubo incumplimiento en la entrega de raciones de alimentos por parte de la empresa proveedora, ")
    n(f"asimismo, se deja constancia que la empresa proveedora {horario} llego en el horario establecido para la entrega de raciones de alimentos contratados. ")
    n(f"Sin mas que hacer constar, se da por finalizada la presente acta en el mismo lugar y fecha, a los catorce (14) minutos de su inicio, a la que se procede a dar lectura por quien suscribe y, {enterado} de su contenido, objeto, validez y efectos legales, acepta, ratifica y firma en una (1) hoja de papel bond carta, impresa unicamente en su anverso, debidamente autorizada por la Contraloria General de Cuentas.")
    return runs


def runs_a_html(runs: list[tuple[str, bool]]) -> str:
    partes = []
    for texto, bold in runs:
        limpio = escape(texto)
        partes.append(f"<b>{limpio}</b>" if bold else limpio)
    return "".join(partes)


def generar_pdf(datos: dict, form: dict, ahora: dt.datetime | None = None) -> bytes:
    buffer = io.BytesIO()
    left, top, right, bottom = 1.30 * inch, 0.80 * inch, 0.45 * inch, 0.35 * inch
    page_w, page_h = letter
    frame_w = page_w - left - right
    frame_h = page_h - top - bottom
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom)
    body = ParagraphStyle("Acta", fontName="Helvetica", fontSize=10, leading=13.2, alignment=TA_JUSTIFY, spaceAfter=0)
    firma = ParagraphStyle("Firma", fontName="Helvetica", fontSize=9, leading=10.5, alignment=TA_CENTER, spaceAfter=0)
    firma_bold = ParagraphStyle("FirmaBold", parent=firma, fontName="Helvetica-Bold")
    nombre = str(datos.get("nombre") or "").upper().strip() or "NO REGISTRADO"
    cargo = capitalizar(datos.get("cargo") or "Encargado")
    mun = capitalizar(datos.get("municipio", ""))
    dep = capitalizar(datos.get("departamento", ""))
    flowables = [
        Paragraph(runs_a_html(generar_runs(datos, form, ahora)), body),
        Spacer(1, 0.42 * inch),
        HRFlowable(width="48%", thickness=0.6, color="black", hAlign="CENTER", spaceAfter=4),
        Paragraph(escape(nombre), firma_bold),
        Paragraph(escape(f"{cargo} del Comedor Social"), firma),
        Paragraph(escape(f"{mun}, {dep}"), firma),
        Paragraph("Subdireccion de Comedores - MIDES", firma),
    ]
    fitted = KeepInFrame(frame_w, frame_h, flowables, mode="shrink", hAlign="LEFT", vAlign="TOP")
    doc.build([fitted])
    return buffer.getvalue()


def cargar_mis_datos() -> dict:
    if not MIS_DATOS_PATH.exists():
        return {}
    try:
        return json.loads(MIS_DATOS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_mis_datos(datos: dict) -> None:
    MIS_DATOS_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def nombre_archivo_acta(no_acta: str) -> str:
    limpio = re.sub(r"[^0-9A-Za-z_-]", "", str(no_acta or "acta")) or "acta"
    return f"Acta_Diaria_{limpio}.pdf"


def datos_ejemplo() -> tuple[dict, dict]:
    datos = {"dpi": "0000000000000", "nombre": "Nombre del Encargado", "comedor": "Cobán", "modalidad": "Fijo", "municipio": "Cobán", "departamento": "Alta Verapaz", "direccion": "Direccion del comedor", "cargo": "Encargado"}
    form = {"no_acta": "1", "empresa": "Banquetes de Guatemala, S.A.", "hora_des": "06:30", "raciones_des": "250", "serie_des": "A", "envio_des": "00045", "ticket_des_ini": "0001", "ticket_des_fin": "0250", "hora_alm": "10:25", "raciones_alm": "350", "serie_alm": "B", "envio_alm": "00046", "ticket_alm_ini": "0001", "ticket_alm_fin": "0350", "sistema": "Sistema de Comedores -SICOME-", "sicome": "600", "sw_hojas": False, "hojas": "0", "incumplimiento": "NO", "horario": "SI"}
    return datos, form


def run_streamlit() -> None:
    import streamlit as st
    st.set_page_config(page_title="Acta Diaria MIDES", page_icon="📄", layout="wide")
    st.title("Asistente para la Generación de Actas")
    st.caption("Acta Diaria · Comedor Social - MIDES")
    guardados = cargar_mis_datos()

    with st.form("acta_form"):
        st.subheader("Mis datos")
        c1, c2 = st.columns(2)
        with c1:
            dpi = st.text_input("DPI / CUI (13 dígitos)", value=guardados.get("dpi", ""))
            comedor = st.text_input("Comedor Social o Dependencia", value=guardados.get("comedor", ""))
            municipio = st.text_input("Municipio", value=guardados.get("municipio", ""))
            direccion = st.text_input("Dirección del comedor", value=guardados.get("direccion", ""))
        with c2:
            nombre = st.text_input("Nombre completo", value=guardados.get("nombre", ""))
            modalidad = st.selectbox("Modalidad", ["Fijo", "Móvil"], index=0 if guardados.get("modalidad", "Fijo") == "Fijo" else 1)
            departamento = st.text_input("Departamento", value=guardados.get("departamento", ""))
            cargo = st.selectbox("Cargo", ["Encargado", "Encargada"], index=0 if guardados.get("cargo", "Encargado") == "Encargado" else 1)

        st.subheader("Datos generales")
        g1, g2 = st.columns([1, 2])
        no_acta = g1.text_input("N° de Acta", value="1")
        empresa = g2.selectbox("Empresa proveedora", ["Banquetes de Guatemala, S.A.", "Tecno Suministros, S.A.", "Proveedora de Alimentos El Rosario"])

        st.subheader("Desayuno")
        d1, d2, d3, d4, d5, d6 = st.columns(6)
        hora_des = d1.text_input("Hora", value="06:30")
        raciones_des = d2.text_input("Raciones", value="250")
        serie_des = d3.text_input("Serie Envío", value="A")
        envio_des = d4.text_input("N° Envío", value="00045")
        ticket_des_ini = d5.text_input("Ticket inicial", value="0001", key="tdi")
        ticket_des_fin = d6.text_input("Ticket final", value="0250", key="tdf")

        st.subheader("Almuerzo")
        a1, a2, a3, a4, a5, a6 = st.columns(6)
        hora_alm = a1.text_input("Hora", value="10:25", key="ha")
        raciones_alm = a2.text_input("Raciones", value="350", key="ra")
        serie_alm = a3.text_input("Serie Envío", value="B", key="sa")
        envio_alm = a4.text_input("N° Envío", value="00046", key="ea")
        ticket_alm_ini = a5.text_input("Ticket inicial", value="0001", key="tai")
        ticket_alm_fin = a6.text_input("Ticket final", value="0350", key="taf")

        st.subheader("Cierre e incidencias")
        x1, x2, x3, x4 = st.columns(4)
        sistema = x1.selectbox("Sistema", ["Sistema de Comedores -SICOME-", "Sistema de Comedores Aplicativo -SICOAPP-"])
        sicome = x2.text_input("Usuarios registrados", value="600")
        sw_hojas = x3.checkbox("Hubo uso de Hojas de Registro")
        hojas = x4.text_input("Usuarios en hojas", value="0", disabled=not sw_hojas)
        y1, y2 = st.columns(2)
        incumplimiento = y1.selectbox("¿Hubo incumplimiento en raciones?", ["NO", "SI"])
        horario = y2.selectbox("¿Llegó en horario establecido?", ["SI", "NO"])
        submitted = st.form_submit_button("Generar acta")

    datos = {"dpi": dpi, "nombre": nombre, "comedor": comedor, "modalidad": modalidad, "municipio": municipio, "departamento": departamento, "direccion": direccion, "cargo": cargo}
    form = {"no_acta": no_acta, "empresa": empresa, "hora_des": hora_des, "raciones_des": raciones_des, "serie_des": serie_des, "envio_des": envio_des, "ticket_des_ini": ticket_des_ini, "ticket_des_fin": ticket_des_fin, "hora_alm": hora_alm, "raciones_alm": raciones_alm, "serie_alm": serie_alm, "envio_alm": envio_alm, "ticket_alm_ini": ticket_alm_ini, "ticket_alm_fin": ticket_alm_fin, "sistema": sistema, "sicome": sicome, "sw_hojas": sw_hojas, "hojas": hojas, "incumplimiento": incumplimiento, "horario": horario}

    col_a, col_b = st.columns([1, 3])
    if col_a.button("Guardar mis datos"):
        guardar_mis_datos(datos)
        st.success("Datos guardados en este equipo.")
    if col_b.button("Borrar mis datos"):
        if MIS_DATOS_PATH.exists():
            MIS_DATOS_PATH.unlink()
        st.info("Datos guardados eliminados.")

    if submitted:
        if not nombre.strip() or not dpi.strip():
            st.error('Escribe al menos "Nombre completo" y "DPI / CUI".')
            return
        pdf_bytes = generar_pdf(datos, form)
        st.download_button("Descargar acta PDF", data=pdf_bytes, file_name=nombre_archivo_acta(no_acta), mime="application/pdf")
        st.success("Acta generada y ajustada a una hoja carta.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generador de Acta Diaria MIDES con ReportLab.")
    parser.add_argument("--demo-pdf", type=Path, help="Genera un PDF de ejemplo en la ruta indicada.")
    args = parser.parse_args()
    if args.demo_pdf:
        datos, form = datos_ejemplo()
        args.demo_pdf.write_bytes(generar_pdf(datos, form))
        print(f"PDF generado: {args.demo_pdf}")
    else:
        run_streamlit()


if __name__ == "__main__":
    main()
