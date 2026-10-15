from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
MODEL_FILE = Path('/root/.pi/agent/models.json')


class ModelFile(BaseModel):
    content: str


@router.get('/api/config/pi-models')
def read_models():
    try:
        return {'content': MODEL_FILE.read_text(encoding='utf-8')}
    except OSError as error:
        raise HTTPException(500, f'读取配置失败：{error}') from None


@router.put('/api/config/pi-models')
def write_models(body: ModelFile):
    try:
        MODEL_FILE.write_text(body.content, encoding='utf-8')
        return {'content': body.content}
    except OSError as error:
        raise HTTPException(500, f'保存配置失败：{error}') from None
