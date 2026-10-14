#include "CS_ClearCtrl.h"

void CS_ClearCtrlFun(void *p)
{
    CS_ClearCtrl *pIp = (CS_ClearCtrl*)p;

    unint32 i;

    /* 三轴喷气脉宽清零 */
    pIp->csJPCData_mPhaseT[0] = 0.0;
    pIp->csJPCData_mPhaseT[1] = 0.0;
    pIp->csJPCData_mPhaseT[2] = 0.0;

    /* 姿控推力器脉宽清零 */
    for (i = 0; i < 12; i++)
    {
        pIp->csJPCData_t[i] = 0.0;
    }

    return;
}