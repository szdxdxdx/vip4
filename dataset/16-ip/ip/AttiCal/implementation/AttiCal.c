#include "AttiCal.h"

void AttiCalFun(void *p) {
    AttiCal *pIp = (AttiCal *)p;

    if ((pIp->workmode) == SAM_CRUISE) { /* 巡航方式 */
        if (pIp->flgSP == TRUE) { /* 太阳可见 */
            pIp->angle[0] = pIp->royaw; /* 滚动角用太敏 */
            pIp->angle[1] = pIp->piyaw; /* 俯仰角用太敏 */
            /* 将太敏读数替换当前积分值 */
            pIp->Gi[0] = pIp->royaw; /* 滚动角陀螺积分  */
            pIp->Gi[1] = pIp->piyaw; /* 俯仰角陀螺积分  */
        } else { /* 太阳不可见 */
            pIp->angle[0] = pIp->Gi[0]; /* 滚动角用陀螺积分 */
            pIp->angle[1] = pIp->Gi[1]; /* 俯仰角用陀螺积分 */
        }
    }
    else { /* 其他模式 */
        pIp->angle[0] = 0.0f; /* 滚动角清零 */
        pIp->angle[1] = 0.0f; /* 俯仰角清零 */
    }

    pIp->rate[0] = pIp->W[0]; /* 滚动角速度用陀螺算出的滚动角速度 */
    pIp->rate[1] = pIp->W[1]; /* 俯仰角速度用陀螺算出的俯仰角速度 */
    pIp->rate[2] = pIp->W[2]; /* 偏航角速度用陀螺算出的偏航角速度 */
    return;
}
