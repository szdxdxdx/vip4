#include "GyroPick.h"

void GyroPickFun(void *p) {
    GyroPick *pIp = (GyroPick *)p;
    unint08 iy;
    float32 tmpgi;

    for (iy = 0; iy < 9; iy++) {

        tmpgi = ABS(pIp->wa[iy] - pIp->wal[iy]); /* 角度增量剔野处理 */

        if (tmpgi > pIp->waThr) { /* 剔野限0.08° */
            pIp->countPick[iy]++; /* 野值计数器 */

            if (pIp->countPick[iy] < pIp->pickThr) { /* 没有6次连续野值 */
                pIp->wa_out[iy] = pIp->wal[iy]; /* 用上周期的值代替本周期的值 */

            } else { /* 连续6周期野值 */
                pIp->wal[iy] = pIp->wa[iy]; /* 用本周期的值代替上周期的值 */
                pIp->wa_out[iy] = pIp->wa[iy];
                pIp->countPick[iy] = 0; /* 替代后，野值计数器清零 */
            }
        } else { /* 没有超出剔野限 */
            pIp->wal[iy] = pIp->wa[iy]; /* 用新值 */
            pIp->wa_out[iy] = pIp->wa[iy];
            pIp->countPick[iy] = 0; /* 野值计数器清零 */
        }
    }
    return;
}
