import subprocess
import time
from collections import Counter
from pathlib import Path

import frontmatter

from schemas.metric import Pendency

ALLOWED_NOTE_EXTENSIONS = ('.md', '.txt')


def get_last_commit(project_path) -> int:
    """Search the last commit timestamp from project."""
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
    """Convert timestamp to text with exact hour

    (round down).
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


def load_frontmatter(file_path: Path) -> dict:
    """Extract metadata from markdown or text frontmatter."""
    try:
        post = frontmatter.load(file_path)
        return post.metadata
    except Exception:
        return {}


def count_note_pendencies(note: Path) -> int:
    """Count unchecked checkboxes (- [ ]) in note file."""
    try:
        return note.read_text(encoding='utf-8').count('- [ ]')
    except Exception:
        return 0


def extract_pendencies(note: Path, project_name: str) -> list[Pendency]:
    """Extract pendency tasks from note content."""
    try:
        content = note.read_text(encoding='utf-8')
    except Exception:
        return []

    results = []
    for line in content.splitlines():
        clean = line.strip()
        if clean.startswith(('- [ ]', '* [ ]')):
            text = clean[5:].strip()
            if text:
                results.append(Pendency(name=text, project_name=project_name))
    return results


def determine_project_status(
    current_status: str,
    project_pendencies: int,
    project_code_path: str,
) -> str:
    """Determine dynamic project status based on pendencies and commit

    recency.
    """
    commit_ts = get_last_commit(project_code_path)
    thirty_days = 30 * 24 * 60 * 60
    time_now = time.time()
    is_recent = commit_ts > 0 and (time_now - commit_ts) <= thirty_days
    is_old = commit_ts > 0 and (time_now - commit_ts) > thirty_days

    if project_pendencies > 0:
        if current_status == 'Concluído':
            if is_old:
                return 'Parado'
            return 'Em desenvolvimento' if is_recent else 'Ideia'
        if current_status == 'Em desenvolvimento' and is_old:
            return 'Parado'
        if current_status == 'Parado' and is_recent:
            return 'Em desenvolvimento'
    elif project_pendencies == 0 and is_recent:
        return 'Concluído'

    return current_status


def sync_project_status(project_dir: Path) -> tuple[str, int]:
    """Synchronize project status in sobre.md and return (status,

    pendencies).
    """
    project_pendencies = 0
    try:
        for n in project_dir.iterdir():
            if n.is_file() and n.suffix.lower() in ALLOWED_NOTE_EXTENSIONS:
                project_pendencies += count_note_pendencies(n)
    except Exception:
        pass

    sobre_file = project_dir / 'sobre.md'
    if not sobre_file.exists() or not sobre_file.is_file():
        return 'Ideia', project_pendencies

    try:
        post = frontmatter.load(sobre_file)
    except Exception:
        return 'Ideia', project_pendencies

    current_status = str(post.get('status', 'Ideia'))
    project_code_path = str(post.get('project_code_path', ''))
    new_status = determine_project_status(
        current_status, project_pendencies, project_code_path
    )

    if new_status != current_status:
        try:
            post['status'] = new_status
            sobre_file.write_text(frontmatter.dumps(post), encoding='utf-8')
        except Exception:
            pass
        return new_status, project_pendencies

    return current_status, project_pendencies


def collect_project_data(
    project: Path,
    tech_counter: Counter,
    all_pendencies: list[Pendency],
) -> tuple[int, str, str]:
    """Collect pendencies, status, and technologies for a given project."""
    pendencies_in_proj = 0
    current_status = 'Ideia'
    project_code_path = ''

    for note in project.iterdir():
        if not (
            note.is_file()
            and note.suffix.lower() in ALLOWED_NOTE_EXTENSIONS
        ):
            continue

        pendencies_in_proj += count_note_pendencies(note)
        all_pendencies.extend(extract_pendencies(note, project.name))

        if note.name == 'sobre.md':
            info = load_frontmatter(note)
            current_status = str(info.get('status', 'Ideia'))
            project_code_path = str(info.get('project_code_path', ''))
            raw_techs = info.get('techs', [])
            if isinstance(raw_techs, list):
                for tech in raw_techs:
                    name = str(tech).strip()
                    if name:
                        tech_counter[name] += 1

    return pendencies_in_proj, current_status, project_code_path
