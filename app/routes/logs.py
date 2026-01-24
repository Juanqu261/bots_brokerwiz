from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse

from config.logging_config import get_log_file_path, get_logs_directory, list_log_files

router = APIRouter(tags=["Logs"])


@router.get(
    "/logs", 
    tags=["Logs"], 
    summary="Ver últimas líneas de un log"
)
async def get_logs(service: str = "api", lines: int = 100):
    """
    Retorna las últimas N líneas del archivo de log.
    
    - **service**: Nombre del servicio (api, mosquitto, worker)
    - **lines**: Número de líneas a retornar (default: 100, max: 1000)
    """
    lines = min(lines, 1000)
    log_file = get_log_file_path(service)
    
    if not log_file.exists():
        return PlainTextResponse(f"No hay logs para '{service}'", status_code=404)
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return PlainTextResponse("".join(last_lines))
    except Exception as e:
        return PlainTextResponse(f"Error leyendo logs: {e}", status_code=500)


@router.get(
    "/logs/download", 
    tags=["Logs"], 
    summary="Descargar archivo de log"
)
async def download_logs(service: str = "api"):
    """
    Descarga el archivo de log completo de un servicio.
    
    - **service**: Nombre del servicio (api, mosquitto, worker)
    """
    log_file = get_log_file_path(service)
    
    if not log_file.exists():
        return PlainTextResponse(f"No hay logs para '{service}'", status_code=404)
    
    return FileResponse(
        path=log_file,
        filename=f"{service}-{log_file.stat().st_mtime:.0f}.log",
        media_type="text/plain"
    )


@router.get(
    "/logs/list", 
    tags=["Logs"], 
    summary="Listar archivos de log"
)
async def list_logs():
    """Lista todos los archivos de log disponibles."""
    return {
        "logs_directory": str(get_logs_directory()),
        "files": list_log_files()
    }
