import subprocess
import time
from pathlib import Path


def get_last_commit(project_path) -> int:
    """Busca o timestamp do último commit na pasta do projeto."""
    if not project_path:
        return 0

    real_path = Path(project_path)
    if not real_path.exists() or not real_path.is_dir():
        return 0

    if not (real_path / '.git').exists():
        return 0

    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ct'],
            cwd=real_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())
    except Exception:
        return 0


def time_formatter(timestamp: int) -> str:
    """Converte um timestamp em segundos para texto relativo

    (arredondando para baixo).
    """
    if timestamp == 0:
        return 'Sem commits'

    difference = time.time() - timestamp

    match difference:
        case d if d < 60:
            res = 'Agora mesmo'
        case d if d < 3600:
            count = int(d // 60)
            res = f'Há {count} minuto{"s" if count > 1 else ""}'
        case d if d < 86400:
            count = int(d // 3600)
            res = f'Há {count} hora{"s" if count > 1 else ""}'
        case d if d < 2592000:
            count = int(d // 86400)
            res = f'Há {count} dia{"s" if count > 1 else ""}'
        case d if d < 31536000:
            count = int(d // 2592000)
            res = f'Há {count} mês' if count == 1 else f'Há {count} meses'
        case d:
            count = int(d // 31536000)
            res = f'Há {count} ano{"s" if count > 1 else ""}'

    return res
