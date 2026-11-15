# Cámaras IP simuladas (desarrollo y demo)

Simula cámaras IP con un servidor RTSP local para probar la lectura en vivo sin cámaras reales y sin
procesar a personas que no dieron su consentimiento. Todo escucha solo en `127.0.0.1`.

## Instalación (una vez)

```bash
cd tools
python fetch_tools.py bin          # MediaMTX v1.21.3 + ffmpeg n9.0 (LGPL), verificados con SHA-256
```

Videos: descargar de Pexels a `tools/videos/` y convertir a 720p / 15 fps:

```bash
bin/ffmpeg/ffmpeg-n9.0-latest-win64-lgpl-9.0/bin/ffmpeg.exe -i videos/pexels_32085182.mp4 -an -vf "scale=1280:-2,fps=15" -c:v libopenh264 -b:v 2M -g 15 videos/comedor.mp4
bin/ffmpeg/ffmpeg-n9.0-latest-win64-lgpl-9.0/bin/ffmpeg.exe -i videos/pexels_1853441.mp4 -an -vf "scale=1280:-2,fps=15" -c:v libopenh264 -b:v 2M -g 15 videos/cafeteria.mp4
```

`bin/` y `videos/` no se suben a git.

## Uso

```bash
cd tools
bin\mediamtx\mediamtx.exe mediamtx.yml
```

Publica en bucle:

| Cámara | URL para SafeRest360 |
|---|---|
| Comedor | `rtsp://127.0.0.1:8554/comedor` |
| Cafetería | `rtsp://127.0.0.1:8554/cafeteria` |

Registra la cámara en la app con esa URL. El backend la empieza a leer en ≤10 s (`STREAM_SYNC_SECONDS`).

## Créditos de los videos (licencia Pexels, uso gratuito)

- "Casual Dining with Friends in Orlando Restaurant", Nielson Caetano-Salmeron — https://www.pexels.com/video/32085182/
- "Video Inside a Coffee Shop on Winter", Lisa Fotios — https://www.pexels.com/video/1853441/

Son videos de archivo públicos, **no** datos recopilados por el equipo.
