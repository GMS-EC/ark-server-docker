<div align="center">
  <h1>🤝 Guía de Contribución / Contributing Guide</h1>
  <p>
    <b>Select Language / Selecciona Idioma:</b><br>
    <a href="#-español"><b>🇪🇸 Español</b></a> &nbsp;|&nbsp; <a href="#-english"><b>🇬🇧 English</b></a>
  </p>
</div>

---

<details open>
<summary><h2 id="-español" style="display:inline-block;">🇪🇸 Español (Haz clic aquí para contraer / desplegar)</h2></summary>

### 🤝 Cómo Contribuir a este Proyecto

¡Gracias por tu interés en contribuir a este contenedor de servidor dedicado de ARK! Toda ayuda es bienvenida, ya sea reportando errores, sugiriendo mejoras o enviando Pull Requests.

---

#### 🐛 Reportar Errores (Bug Reports)

Antes de abrir un issue, por favor revisa la lista de issues existentes para evitar duplicados. Al reportar un problema, asegúrate de incluir:

1. **Versión / Tag de la imagen utilizada** (ej. `marcusm99/ark-server-docker:latest` o hash del commit).
2. **Nombre del Mapa (`WORLD`)** (ej. `TheIsland`, `ScorchedEarth_P`, `Ragnarok`, etc.).
3. **Lista de Mods Activos (`MOD_IDS`)** (ej. `731604991,893735676` o especificar si no usas mods).
4. **Logs relevantes del contenedor**:
   ```bash
   docker compose logs --tail 100
   ```
5. **Pasos detallados para reproducir el problema**.

---

#### 💡 Proponer Nuevas Funcionalidades

Si tienes una idea para mejorar el contenedor:
- Abre un issue utilizando la plantilla de **Feature Request**.
- Describe claramente el caso de uso y por qué sería útil para otros usuarios.

---

#### 🔀 Enviar un Pull Request (PR)

1. Haz un Fork del repositorio y crea una rama descriptiva (`git checkout -b feature/nueva-funcionalidad`).
2. Sigue las convenciones de código existentes en el proyecto.
3. Asegúrate de verificar la sintaxis de todos los scripts Bash:
   ```bash
   for f in scripts/*.sh; do bash -n "$f"; done
   ```
4. Envía tu PR hacia la rama `main` explicando detalladamente los cambios propuestos.

</details>

---

<details>
<summary><h2 id="-english" style="display:inline-block;">🇬🇧 English (Click here to expand / collapse)</h2></summary>

### 🤝 How to Contribute to this Project

Thank you for your interest in contributing to this ARK dedicated server container! All contributions are welcome, whether reporting bugs, suggesting features, or submitting Pull Requests.

---

#### 🐛 Reporting Bugs

Before opening an issue, please search existing issues to avoid duplicates. When reporting a bug, please make sure to include:

1. **Image Version / Tag used** (e.g. `marcusm99/ark-server-docker:latest` or commit hash).
2. **Map Name (`WORLD`)** (e.g. `TheIsland`, `ScorchedEarth_P`, `Ragnarok`, etc.).
3. **Active Mods List (`MOD_IDS`)** (e.g. `731604991,893735676` or specify if none).
4. **Relevant Container Logs**:
   ```bash
   docker compose logs --tail 100
   ```
5. **Detailed steps to reproduce the issue**.

---

#### 💡 Feature Requests

If you have an idea to improve the container:
- Open an issue using the **Feature Request** template.
- Clearly describe your use case and why it would benefit other users.

---

#### 🔀 Submitting a Pull Request (PR)

1. Fork the repository and create a feature branch (`git checkout -b feature/my-new-feature`).
2. Follow the project's existing code style and guidelines.
3. Ensure all Bash scripts pass syntax verification:
   ```bash
   for f in scripts/*.sh; do bash -n "$f"; done
   ```
4. Submit your PR targeting the `main` branch with a detailed explanation of your changes.

</details>
