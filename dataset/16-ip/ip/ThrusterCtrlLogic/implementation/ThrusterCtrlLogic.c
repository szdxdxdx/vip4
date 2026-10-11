#include "ThrusterCtrlLogic.h"

void ThrusterCtrlLogicFun(void *p) {
    ThrusterCtrlLogic *pIp = (ThrusterCtrlLogic *)p;
    pIp->wPulse = 0;
    if (pIp->Yp[0] != 0) { /* 伪速率状态量 */
        pIp->wPulse = pIp->wPulse | 0x04; /* 软件喷气变量 */
    }

    if (pIp->Yn[0] != 0) { /* 伪速率状态量 */
        pIp->wPulse = pIp->wPulse | 0x08; /* 软件喷气变量 */
    }

    if (pIp->Yp[1] != 0) { /* 伪速率状态量 */
        pIp->wPulse = pIp->wPulse | 0x10; /* 软件喷气变量 */
    }

    if (pIp->Yn[1] != 0) { /* 伪速率状态量 */
        pIp->wPulse = pIp->wPulse | 0x20; /* 软件喷气变量 */
    }

    if (pIp->Yp[2] != 0) { /* 伪速率状态量 */
        pIp->wPulse = pIp->wPulse | 0x40; /* 软件喷气变量 */
    }

    if (pIp->Yn[2] != 0) { /* 伪速率状态量 */
        pIp->wPulse = pIp->wPulse | 0x80; /* 软件喷气变量 */
    }
    return;
}
