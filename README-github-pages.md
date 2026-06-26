# Acta Diaria - GitHub Pages

Esta carpeta está lista para publicarse con GitHub Pages como sitio estático.

## Archivos importantes

- `index.html`: aplicación web principal.
- `.nojekyll`: evita procesamiento innecesario de GitHub Pages.

## Publicación rápida

1. Crea un repositorio en GitHub.
2. Sube el contenido de esta carpeta `outputs` a la raíz del repositorio.
3. En GitHub: Settings > Pages.
4. En "Build and deployment", selecciona "Deploy from a branch".
5. Selecciona branch `main` y carpeta `/root`.
6. Guarda y espera el enlace público.

Nota: GitHub Pages no ejecuta Python ni Streamlit. Por eso esta versión usa JavaScript y pdfmake en el navegador.
