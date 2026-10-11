#include "GyroAngCal.h"


static float32 ModPNHP(float32 value, float32 limit) {
    if (value > limit) {
        value = limit;
    } else if(value < -limit) {
        value = -limit;
    }
    return value;
}


void GyroAngCalFun(void *p) {
    GyroAngCal *pIp = (GyroAngCal *)p;

    float32 dgi[3];
    /* SAM不进行陀螺漂移补偿 */
    dgi[0] = pIp->Gi[0] + pIp->W[0] * pIp->ctlPeriod; /* 控制周期0.16 */
    dgi[1] = pIp->Gi[1] + pIp->W[1] * pIp->ctlPeriod;
    dgi[2] = pIp->Gi[2] + pIp->W[2] * pIp->ctlPeriod;

    /* 陀螺角度积分,限在(-180, 180)之间 */
    pIp->Gi[0] = ModPNHP(dgi[0], 180.0f); /* 滚动角积分 = 上周期积分总值 + 本周期积分改变值 */
    pIp->Gi[1] = ModPNHP(dgi[1], 180.0f);
    pIp->Gi[2] = ModPNHP(dgi[2], 90.0f);
    return;
}
