# Acta Diaria ReportLab

Aplicacion Python/Streamlit para generar el Acta Diaria en PDF carta de una sola hoja.

## Uso

1. Instala dependencias si hace falta:

   pip install -r requirements-acta-diaria.txt

2. Ejecuta la app:

   streamlit run acta_diaria_reportlab_app.py

3. Para generar un PDF de prueba sin abrir Streamlit:

   python acta_diaria_reportlab_app.py --demo-pdf Acta_Diaria_demo.pdf

El PDF usa ReportLab y KeepInFrame(mode="shrink") para ajustar el contenido completo, incluida la firma, dentro de una hoja carta.
