#include "PowerOnJudge.h"

/* IP实体 */
void PowerOnJudgeFun(void *pIp) {
    PowerOnJudge *p = (PowerOnJudge *)pIp;
    unint32 powerState = p->powerState;

    /* 本周期电源状态为断电 */
    if (powerState == DEV_INVALID) {
        if (p->cntPowerOff < p->numOffPeriod) {
            p->cntPowerOff++;
        } else {
            /* 已断电 */
            p->cntPowerOn = 0;
            p->powerPr1 = DEV_INVALID;
            p->bPowerOnOk = FALSE32;
        }
    } else if ((p->powerPr1 == DEV_INVALID) && (powerState == DEV_POWERON)) { /* 电源状态由断电变加电 */
        p->cntPowerOn++;

        if (p->cntPowerOn > p->numOnPeriod) {
            p->cntPowerOff = 0;
            /* 认为已加电大于30s */
            p->bPowerOnOk = TRUE32;
        } else {
            /* 加电不足30s,延续上一周期的电源状态 */
            powerState = DEV_INVALID;
        }
    } else {
        /* 电源状态没有发生变化 */
        NULL_STATEMENT();
    }
    /* 保存本周期电源状态 */
    p->powerPr1 = powerState;
    return;
}