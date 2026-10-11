#include "Fg333saUnPack.h"

/*
fg_3_3_3sa协议解析IP
*/
void Fg333saUnPackFun(void *pIp) {
    Fg333saUnPack *p = (Fg333saUnPack *)pIp;

    unint32 temp_var;

    temp_var = UI32_MAKE(p->pRecvbuf[2], p->pRecvbuf[3], p->pRecvbuf[4], p->pRecvbuf[5]);
    p->wt0 = ((float64)(siint32)temp_var) / 3.0e6 * DEG2RAD;

    p->glwd1 = UI16_MAKE(p->pRecvbuf[6], p->pRecvbuf[7]);
    p->glwd2 = UI16_MAKE(p->pRecvbuf[8], p->pRecvbuf[9]);
    p->dlwd = UI16_MAKE(p->pRecvbuf[10], p->pRecvbuf[11]);

    p->status = p->pRecvbuf[16];

    /* 陀螺计算角度增量 */
    p->gf = p->wt0 * p->dtime;
    return;
}
