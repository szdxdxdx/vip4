"""整个任务的安全 ZIP 快照，临时文件由响应完成后清理。"""
import os
import stat
import tempfile
import zipfile
from pathlib import Path

from .task import Task, TaskPathError


def task_archive(task_id):
    directory = Task._task_dir(task_id)
    fd, name = tempfile.mkstemp(suffix='.zip')
    os.close(fd)
    archive = Path(name)
    try:
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
            # dir_fd 与 O_NOFOLLOW 防止检查之后被替换为外部链接。
            def add(root_fd, relative):
                for name in sorted(os.listdir(root_fd)):
                    info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                    path = relative / name
                    if stat.S_ISDIR(info.st_mode):
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
                        try:
                            output.writestr(path.as_posix() + '/', b'')
                            add(child, path)
                        finally:
                            os.close(child)
                    elif stat.S_ISREG(info.st_mode):
                        child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
                        with os.fdopen(child, 'rb') as source:
                            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                                raise TaskPathError('任务 ZIP 不允许特殊文件', 400)
                            with output.open(path.as_posix(), 'w', force_zip64=True) as target:
                                while block := source.read(1024 * 1024):
                                    target.write(block)
                    else:
                        raise TaskPathError('任务 ZIP 不允许符号链接或特殊文件', 400)
            root_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                output.writestr(task_id + '/', b'')
                add(root_fd, Path(task_id))
            finally:
                os.close(root_fd)
        return archive
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
