#include "GyroStateSet.h"

void GyroStateSetFun(void *p) {
    GyroStateSet *pIp = (GyroStateSet *)p;

    unint08 si;
    unint16 tmpFOGPS;
    unint16 tmpPSBIT;
    unint16 tmpHTBIT;

    for (si = 0; si < 9; si++) { /* 9个陀螺 */
        tmpPSBIT = pIp->powerState & (1 << si);  /* 找上电 */
        tmpHTBIT = pIp->healthState & (1 << si); /* 找健康 */

        if ((tmpPSBIT != 0) && (tmpHTBIT == 0)) { /* 上电且健康 */
            pIp->StateFlag[si] = TRUE; /* 陀螺状态标志为正常 */
        } else {
            pIp->StateFlag[si] = FALSE; /* 陀螺状态标志为不正常 */
        }
    }
    return;
}
