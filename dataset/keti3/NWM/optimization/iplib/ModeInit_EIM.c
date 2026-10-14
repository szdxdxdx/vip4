#include "ModeInit_EIM.h"

void ModeInit_EIMFun(void *p)
{
    ModeInit_EIM *pIp = (ModeInit_EIM*)p;

    pIp->csMnvData_A_Trgt[0] = 0.0;
    pIp->csMnvData_A_Trgt[1] = 0.0;
    pIp->csMnvData_A_Trgt[2] = 0.0;

    return;
}