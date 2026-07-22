<div align="center">
  <h1>🌐 Guía de Conexión al Servidor / Connection Guide</h1>
  <p>
    <b>Select Language / Selecciona Idioma:</b><br>
    <a href="#-español"><b>🇪🇸 Español</b></a> &nbsp;|&nbsp; <a href="#-english"><b>🇬🇧 English</b></a>
  </p>
</div>

---

<details open>
<summary><h2 id="-español" style="display:inline-block;">🇪🇸 Español (Haz clic aquí para contraer / desplegar)</h2></summary>

### 🌐 Guía Práctica de Conexión al Servidor de ARK

Esta guía explica los métodos probados y más confiables para conectarte a tu servidor dedicado de ARK en Docker, ya sea en tu red local (LAN), jugando con amigos sin abrir puertos mediante **ZeroTier**, o mediante redirección de puertos tradicional en tu router.

> [!TIP]
> **Nota sobre el buscador de ARK:** El filtro nativo de "LAN" dentro del buscador del juego ARK suele ser inestable y a menudo no muestra servidores en Docker. **El método universal más rápido y confiable es agregar el servidor a los Favoritos de Steam.**

---

#### ⭐ Método 1: Agregar el Servidor a Favoritos de Steam (Recomendado)

Este es el método oficial que funciona tanto en Red Local (LAN), como en ZeroTier o con Puertos Públicos.

1. Abre la aplicación de **Steam** en tu PC.
2. En el menú superior de Steam, ve a **Ver** (View) ➔ **Servidores de juegos** (Game Servers).
3. Selecciona la pestaña **Favoritos** (Favorites).
4. Haz clic en el botón con el signo **`+`** (Agregar un servidor).
5. Introduce la dirección IP del servidor agregando el **`QUERY_PORT`** (por defecto `27015`):
   - **Si el servidor está en tu red local (ej. servidor Ubuntu en casa):** `192.168.1.X:27015` *(reemplaza por la IP de tu servidor)*.
   - **Si usas ZeroTier con amigos:** `IP_VIRTUAL_ZEROTIER:27015` (ejemplo: `10.147.20.105:27015`).
   - **Si abriste puertos en tu router:** `TU_IP_PUBLICA:27015`.
6. Haz clic en **Aceptar**. El servidor aparecerá de inmediato en tu lista.
7. Abre **ARK: Survival Evolved**, ve a **Unirse a ARK** y cambia el filtro de la esquina inferior izquierda a **Favoritos**. ¡Tu servidor aparecerá ahí listo para entrar!

---

#### 🔒 Método 2: Conectar sin abrir puertos usando ZeroTier (VPN Virtual)

Si tu proveedor de internet (ISP) utiliza CGNAT, no tienes acceso a la configuración de tu router o **no quieres abrir puertos públicos por seguridad**, ZeroTier es la mejor opción. Crea una red local virtual encriptada entre tu servidor y tus amigos.

##### Paso 1: Crear la Red en ZeroTier
1. Entra a [zerotier.com](https://www.zerotier.com/) y crea una cuenta gratuita.
2. Haz clic en **Create a Network** y copia el **Network ID** de 16 caracteres.

##### Paso 2: Unir el Servidor a la Red
1. Instala ZeroTier en la máquina que corre Docker (ej. Ubuntu Server):
   ```bash
   curl -s https://install.zerotier.com | sudo bash
   sudo zerotier-cli join TU_NETWORK_ID
   ```
2. Entra al panel de ZeroTier Central ➔ pestaña **Members** y autoriza (marca la casilla **Auth**) al servidor.
3. Anota la **IP Virtual de ZeroTier** asignada al servidor (ejemplo: `10.147.20.105`).

##### Paso 3: Unir a tus Amigos y Conectar
1. Tus amigos instalan ZeroTier en sus PCs y ejecutan `zerotier-cli join TU_NETWORK_ID`.
2. Autoriza a tus amigos en el panel de ZeroTier Central.
3. **Tus amigos agregan la IP de ZeroTier a Steam:** Van a *Steam ➔ Ver ➔ Servidores de juegos ➔ Favoritos ➔ Agregar servidor* e introducen `10.147.20.105:27015`.
4. ¡El servidor les aparecerá en la pestaña Favoritos dentro de ARK!

---

#### 🌐 Método 3: Conexión por Internet Abriendo Puertos (Port Forwarding)

Si posees una IP pública accesible y control sobre tu router:

1. Ingresa al panel de administración de tu Router.
2. Redirecciona los siguientes puertos hacia la IP local de tu servidor (ej. `192.168.1.50`):
   - **`7777` UDP** (Puerto principal del juego)
   - **`27015` UDP** (Puerto de consultas de Steam Query)
   - **`27020` TCP** (Opcional - Puerto RCON)
3. **Firewall del Sistema Operativo (`ufw` en Ubuntu):** Si el servidor se ejecuta en una máquina con `ufw` activo, abre también los puertos a nivel de sistema operativo:
   ```bash
   sudo ufw allow 7777/udp
   sudo ufw allow 27015/udp
   sudo ufw allow 27020/tcp
   ```
   *(Este paso solo aplica si `ufw` u otro firewall del SO está activo en la máquina host; no es necesario si el firewall del sistema está deshabilitado).*
4. Tus amigos agregan en Steam Favoritos: `TU_IP_PUBLICA:27015`.

---

#### 💻 Método 4: Mediante Consola in-game (Opción Alternativa)

Debido a que ARK no permite abrir la consola en el menú principal:
1. Inicia ARK y entra a cualquier partida local o mapa singleplayer.
2. Presiona la tecla **`Tab`** para desplegar la consola de comandos.
3. Escribe:
   ```text
   open IP_DEL_SERVIDOR:7777
   ```
4. Presiona **Enter** para conectarte directamente.

</details>

---

<details>
<summary><h2 id="-english" style="display:inline-block;">🇬🇧 English (Click here to expand / collapse)</h2></summary>

### 🌐 Practical ARK Server Connection Guide

This guide covers the most tested and reliable methods to connect to your dedicated ARK server running in Docker, whether on your local network (LAN), playing with friends without opening ports via **ZeroTier**, or using traditional router port forwarding.

> [!TIP]
> **Note on ARK Server Browser:** The native "LAN" filter inside the ARK in-game server browser is often unreliable with Docker containers. **The universal, fastest, and most reliable method is adding the server to Steam Favorites.**

---

#### ⭐ Method 1: Adding the Server to Steam Favorites (Recommended)

This official method works universally for Local LAN, ZeroTier, and Public Ports.

1. Open the **Steam** desktop application.
2. In the top Steam menu, go to **View** ➔ **Game Servers**.
3. Select the **Favorites** tab.
4. Click the **`+`** button (Add a server).
5. Enter the server's IP address along with the **`QUERY_PORT`** (default `27015`):
   - **For local LAN (e.g. Ubuntu server at home):** `192.168.1.X:27015` *(replace with your server IP)*.
   - **Using ZeroTier with friends:** `ZEROTIER_VIRTUAL_IP:27015` (e.g. `10.147.20.105:27015`).
   - **Using Public Port Forwarding:** `YOUR_PUBLIC_IP:27015`.
6. Click **OK**. The server will appear in your Steam list.
7. Open **ARK: Survival Evolved**, click **Join ARK**, and change the bottom-left filter to **Favorites**. Your server will appear ready to join!

---

#### 🔒 Method 2: Connecting Without Port Forwarding via ZeroTier (Virtual VPN)

If your ISP uses CGNAT or you **do not want to open public ports for security reasons**, ZeroTier creates a secure peer-to-peer encrypted virtual local network between your server and friends.

##### Step 1: Create a ZeroTier Network
1. Sign up for a free account at [zerotier.com](https://www.zerotier.com/).
2. Click **Create a Network** and copy the 16-character **Network ID**.

##### Step 2: Join the Server to the Network
1. Install ZeroTier on the server machine (e.g. Ubuntu Server):
   ```bash
   curl -s https://install.zerotier.com | sudo bash
   sudo zerotier-cli join YOUR_NETWORK_ID
   ```
2. Open ZeroTier Central ➔ **Members** tab and check **Auth** to authorize the server.
3. Note the **ZeroTier Virtual IP** assigned to the server (e.g. `10.147.20.105`).

##### Step 3: Join Friends & Connect
1. Have friends install ZeroTier and run `zerotier-cli join YOUR_NETWORK_ID`.
2. Authorize them in ZeroTier Central.
3. **Friends add the ZeroTier IP to Steam:** Go to *Steam ➔ View ➔ Game Servers ➔ Favorites ➔ Add Server* and enter `10.147.20.105:27015`.
4. The server will appear under the Favorites tab in ARK!

---

#### 🌐 Method 3: Public Internet Connection via Port Forwarding

If you have a public IP and access to your router settings:

1. Open your Router admin panel.
2. Forward the following ports to your server's local IP (e.g. `192.168.1.50`):
   - **`7777` UDP** (Main Game Port)
   - **`27015` UDP** (Steam Query Port)
   - **`27020` TCP** (Optional - RCON Port)
3. **Host OS Firewall (`ufw` on Ubuntu):** If the server runs on a host with `ufw` enabled, allow the ports at the OS level as well:
   ```bash
   sudo ufw allow 7777/udp
   sudo ufw allow 27015/udp
   sudo ufw allow 27020/tcp
   ```
   *(This step is only necessary if `ufw` or another OS firewall is active on the host machine; skip if the system firewall is disabled).*
4. Friends add `YOUR_PUBLIC_IP:27015` to Steam Favorites.

---

#### 💻 Method 4: Via In-Game Console (Alternative Option)

Since ARK doesn't allow opening the console in the main menu:
1. Launch ARK and join any local singleplayer map.
2. Press **`Tab`** to open the command console.
3. Type:
   ```text
   open SERVER_IP:7777
   ```
4. Press **Enter** to connect.

</details>
