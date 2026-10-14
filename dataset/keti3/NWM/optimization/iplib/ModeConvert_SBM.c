#include "NWM.h"
#include "ModeConvert_SBM.h"

void ModeConvert_SBMFun(void *p)
{
    ModeConvert_SBM *pIp = (ModeConvert_SBM*)p;

    if((StarTime - t0) >= dt_OrbitInject)
    /* if (m_starTime >= csModePara.dt_OrbitInject) */
    {
        WorkMode = 0x01u;
    }

    return;
}