#include "CS_StarTimeNextCalc.h"

void CS_StarTimeNextCalcFun(void *p)
{
    CS_StarTimeNextCalc *pIp = (CS_StarTimeNextCalc*)p;

    if(pIp->csOrbDataOther_F_DTOrbitEUpdate == 1)
    {
        pIp->m_starTime_Next = pIp->m_starTime + pIp->m_DeltaT;
    }
    else
    {
        pIp->m_starTime_Next = pIp->m_starTime_Next + pIp->m_DeltaT;
    }

    return;
}