"""课题五伪后端，仅用于本机联调，不保存上传压缩包。"""
import logging
import os
import zipfile

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

app = FastAPI()
records = []
logger = logging.getLogger('tmp_keti5')


class Callback(BaseModel):
    executionId: str
    jobName: str
    buildId: int
    toolName: str
    progress: int
    status: int


@app.post('/demo-callback/notify')
def notify(body: Callback):
    record = body.model_dump()
    records.append(record)
    logger.info('进度 %s', record)
    return {'success': True, **record, 'completed': body.status == 1}


@app.post('/sw/idep/plugin/reportUpload')
def upload(file: UploadFile = File(), pipelineName: str = Form(),
           buildId: str = Form(), toolName: str = Form()):
    with zipfile.ZipFile(file.file) as archive:
        files = archive.namelist()
        if archive.testzip() is not None:
            return {'code': 400}
    record = {'pipelineName': pipelineName, 'buildId': buildId, 'toolName': toolName, 'files': files}
    records.append(record)
    logger.info('上传 %s', record)
    return {'code': 200}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('KETI5_MOCK_PORT', '50055')))
