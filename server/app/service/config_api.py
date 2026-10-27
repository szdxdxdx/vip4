from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ..vip_task import config

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


class KetiConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    KETI2_BASE_URL: str
    KETI3_BASE_URL: str
    KETI5_CALLBACK_URL: str
    KETI5_UPLOAD_URL: str
    KETI5_JENKINS_USER: str
    KETI5_JENKINS_API_TOKEN: str


@router.get('/api/config/keti-ip')
def read_keti_config():
    return config.get_keti_config()


@router.put('/api/config/keti-ip')
def write_keti_config(body: KetiConfig):
    try:
        config.save_keti_config(body.model_dump())
    except OSError:
        raise HTTPException(500, '保存课题配置失败，请检查配置目录权限及磁盘空间') from None
    return {'status': 'saved'}
