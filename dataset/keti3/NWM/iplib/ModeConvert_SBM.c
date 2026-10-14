#include "ModeConvert_SBM.h"

void ModeConvert_SBMFun(void *p)
{
    ModeConvert_SBM *pIp = (ModeConvert_SBM*)p;

    if((pIp->m_starTime - pIp->csOrb19_Para_I_t0) >= pIp->csModePara_dt_OrbitInject)
    /* if (m_starTime >= csModePara.dt_OrbitInject) */
    {
        pIp->m_WorkMode = 0x01u;
    }

    return;
}