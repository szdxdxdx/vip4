#include "ModeInit_NWM.h"

void ModeInit_NWMFun(void *p)
{
    ModeInit_NWM *pIp = (ModeInit_NWM*)p;

    pIp->csMnvData_A_Trgt[0] = 0.0;
    pIp->csMnvData_A_Trgt[1] = 0.0;
    pIp->csMnvData_A_Trgt[2] = 0.0;

    return;
}